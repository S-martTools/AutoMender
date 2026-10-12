from __future__ import annotations

import itertools
from typing import Dict, Mapping, Sequence, Tuple

import torch
import torch.nn.functional as F

from ..models.cmoe_lora import CMoECausalLM


def conflict_regularization(repair_loss: torch.Tensor, model: CMoECausalLM, active_experts: Sequence, create_graph: bool = True) -> Tuple[torch.Tensor, Dict[str, float]]:
    if active_experts and isinstance(active_experts[0], (list, tuple, set)):
        unique = list(dict.fromkeys(label for labels in active_experts for label in labels))
        requested_pairs = {tuple(sorted(pair)) for labels in active_experts for pair in itertools.combinations(dict.fromkeys(labels), 2)}
    else:
        unique = list(dict.fromkeys(active_experts))
        requested_pairs = {tuple(sorted(pair)) for pair in itertools.combinations(unique, 2)}
    if not requested_pairs:
        zero = repair_loss.new_zeros(())
        return zero, {"mean_cosine": 0.0, "conflict_rate": 0.0, "pairs": 0.0}
    vectors = {}
    for index, name in enumerate(unique):
        parameters = model.adapter_parameters(name)
        gradients = torch.autograd.grad(repair_loss, parameters, retain_graph=True, create_graph=create_graph, allow_unused=True)
        pieces = [gradient.reshape(-1) for gradient in gradients if gradient is not None]
        vectors[name] = torch.cat(pieces) if pieces else repair_loss.new_zeros(1)
    cosines = []
    penalties = []
    for left, right in sorted(requested_pairs):
        cosine = F.cosine_similarity(vectors[left], vectors[right], dim=0, eps=1e-8)
        cosines.append(cosine)
        penalties.append(torch.relu(-cosine))
    stacked = torch.stack(cosines)
    loss = torch.stack(penalties).mean()
    return loss, {
        "mean_cosine": float(stacked.detach().mean().cpu()),
        "conflict_rate": float((stacked.detach() < 0).float().mean().cpu()),
        "pairs": float(len(cosines)),
    }


def incremental_communication_regularization(repair_loss: torch.Tensor, model: CMoECausalLM, reference_gradients: Mapping[str, torch.Tensor], create_graph: bool = True) -> torch.Tensor:
    named = [(name, parameter) for name, parameter in model.named_parameters() if ".communication." in name and parameter.requires_grad]
    gradients = torch.autograd.grad(repair_loss, [parameter for _, parameter in named], retain_graph=True, create_graph=create_graph, allow_unused=True)
    terms = []
    for (name, _), gradient in zip(named, gradients):
        if gradient is not None and name in reference_gradients:
            terms.append((gradient - reference_gradients[name].to(gradient.device)).pow(2).sum())
    if not terms:
        return next(model.parameters()).new_zeros(())
    return torch.stack(terms).mean()
