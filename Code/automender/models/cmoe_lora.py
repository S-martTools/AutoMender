from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import torch
from torch import nn

from ..taxonomy import EXPERT_CATEGORIES


class LoRAAdapter(nn.Module):
    def __init__(self, in_features: int, out_features: int, rank: int = 8, alpha: float = 32.0, dropout: float = 0.1):
        super().__init__()
        self.rank, self.scaling = rank, alpha / rank
        self.dropout = nn.Dropout(dropout)
        self.A = nn.Linear(in_features, rank, bias=False)
        self.B = nn.Linear(rank, out_features, bias=False)
        nn.init.normal_(self.A.weight, mean=0.0, std=1.0 / math.sqrt(rank))
        nn.init.zeros_(self.B.weight)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.B(self.A(self.dropout(value))) * self.scaling


class CMoELinear(nn.Module):
    def __init__(self, base: nn.Linear, experts: Sequence[str] = EXPERT_CATEGORIES, rank: int = 8, alpha: float = 32.0, dropout: float = 0.1, lambda_comm: float = 1.0):
        super().__init__()
        self.base = base
        for parameter in self.base.parameters():
            parameter.requires_grad_(False)
        self.experts = nn.ModuleDict({name: LoRAAdapter(base.in_features, base.out_features, rank, alpha, dropout) for name in experts})
        self.communication = LoRAAdapter(base.in_features, base.out_features, rank, alpha, dropout)
        self.lambda_comm = float(lambda_comm)
        self.active_experts: Union[List[str], List[List[str]]] = []
        self.communication_enabled = True

    def set_route(self, labels: Union[Sequence[str], Sequence[Sequence[str]]], communication: bool = True) -> None:
        self.active_experts = [list(item) for item in labels] if labels and isinstance(labels[0], (list, tuple, set)) else list(labels)  # type: ignore[index]
        self.communication_enabled = communication

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        output = self.base(value)
        if self.communication_enabled:
            output = output + self.lambda_comm * self.communication(value)
        active = self.active_experts
        if active and isinstance(active[0], list):
            if value.shape[0] != len(active):
                raise ValueError("per-example routing length must equal batch size")
            for name in self.experts:
                selected = torch.tensor([name in labels for labels in active], device=value.device, dtype=torch.bool)
                mask = selected.to(dtype=value.dtype)
                if bool(selected.any()):
                    shape = [len(active)] + [1] * (value.dim() - 1)
                    output = output + self.experts[name](value) * mask.view(*shape)
        else:
            for name in active:
                if name not in self.experts:
                    raise ValueError("unknown CMoE expert: %s" % name)
                output = output + self.experts[name](value)
        return output


def inject_cmoe_lora(model: nn.Module, target_modules: Sequence[str], rank: int = 8, alpha: float = 32.0, dropout: float = 0.1, lambda_comm: float = 1.0) -> List[str]:
    replaced: List[str] = []
    for full_name, module in list(model.named_modules()):
        if not isinstance(module, nn.Linear) or not any(full_name.endswith(target) for target in target_modules):
            continue
        parent_name, _, child_name = full_name.rpartition(".")
        parent = model
        if parent_name:
            for component in parent_name.split("."):
                parent = getattr(parent, component)
        setattr(parent, child_name, CMoELinear(module, rank=rank, alpha=alpha, dropout=dropout, lambda_comm=lambda_comm))
        replaced.append(full_name)
    if not replaced:
        raise ValueError("No target linear modules found: %s" % ", ".join(target_modules))
    return replaced


class CMoECausalLM(nn.Module):
    def __init__(self, base_model: nn.Module):
        super().__init__()
        self.base_model = base_model
        self.value_head: Optional[nn.Linear] = None

    def cmoe_layers(self) -> Iterable[CMoELinear]:
        return (module for module in self.modules() if isinstance(module, CMoELinear))

    def set_route(self, labels: Union[Sequence[str], Sequence[Sequence[str]]], communication: bool = True) -> None:
        for layer in self.cmoe_layers():
            layer.set_route(labels, communication)

    def forward(self, *args, expert_labels=(), communication=True, **kwargs):
        self.set_route(expert_labels, communication)
        return self.base_model(*args, **kwargs)

    def generate(self, *args, expert_labels=(), communication=True, **kwargs):
        self.set_route(expert_labels, communication)
        return self.base_model.generate(*args, **kwargs)

    def add_value_head(self, hidden_size: int) -> nn.Linear:
        self.value_head = nn.Linear(hidden_size, 1)
        return self.value_head

    def adapter_parameters(self, expert: Optional[str] = None) -> List[nn.Parameter]:
        parameters: List[nn.Parameter] = []
        for layer in self.cmoe_layers():
            adapter = layer.communication if expert in (None, "communication") else layer.experts[expert]
            parameters.extend(adapter.parameters())
        return parameters

    def save_adapters(self, output_dir: str, metadata: Optional[Mapping[str, object]] = None) -> None:
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        state = {name: value.cpu() for name, value in self.state_dict().items() if ".experts." in name or ".communication." in name or name.startswith("value_head")}
        torch.save(state, target / "adapters.pt")
        (target / "adapter_config.json").write_text(json.dumps(dict(metadata or {}), indent=2), encoding="utf-8")

    def load_adapters(self, directory: str) -> None:
        state = torch.load(Path(directory) / "adapters.pt", map_location="cpu")
        missing, unexpected = self.load_state_dict(state, strict=False)
        if unexpected:
            raise ValueError("Unexpected adapter keys: %s" % unexpected)


def freeze_for_stage(model: CMoECausalLM, stage: str, active_experts: Sequence[str] = (), communication: bool = True) -> None:
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    for layer in model.cmoe_layers():
        if communication:
            for parameter in layer.communication.parameters():
                parameter.requires_grad_(True)
        if stage != "dapt":
            for name in active_experts:
                for parameter in layer.experts[name].parameters():
                    parameter.requires_grad_(True)
    if stage == "ppo" and model.value_head is not None:
        for parameter in model.value_head.parameters():
            parameter.requires_grad_(True)
