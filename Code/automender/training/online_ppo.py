from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import torch
from torch.utils.data import DataLoader, Dataset

from ..models.cmoe_lora import CMoECausalLM, freeze_for_stage
from ..models.generation import parse_repair_output
from ..taxonomy import EXPERT_CATEGORIES
from ..utils import read_jsonl, write_json
from .engine import load_model
from .ppo import ppo_loss, terminal_returns


class RolloutDataset(Dataset):
    def __init__(self, path: str, tokenizer: Any, max_length: int, paper: bool = True, candidates: int = 4):
        self.rows = list(read_jsonl(path))
        if paper and any(not row.get("paper_eligible", False) for row in self.rows):
            raise RuntimeError("Paper PPO rejects fake/unverified rollout rewards")
        if paper:
            for row in self.rows:
                quality = row.get("quality") or {}
                expected = 1.0 / (1.0 + float(quality.get("total_cost", 0.0))) if quality.get("valid") else -1.0
                if abs(float(row.get("reward", 99.0)) - expected) > 1e-8:
                    raise RuntimeError("PPO reward does not match Eq. 16 quality artifact")
                if not parse_repair_output(row.get("completion", "")).parse_ok:
                    raise RuntimeError("PPO candidate is not a complete repair contract")
        groups = Counter(str(row.get("group_id", "")) for row in self.rows)
        if any(not key or value != candidates for key, value in groups.items()):
            raise ValueError("Every PPO input group must contain exactly %d complete candidates" % candidates)
        self.tokenizer, self.max_length = tokenizer, max_length

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index: int) -> Dict[str, Any]:
        row = self.rows[index]
        prompt_ids = self.tokenizer(row["prompt"], add_special_tokens=True)["input_ids"]
        all_ids = self.tokenizer(row["prompt"] + row["completion"], truncation=True, max_length=self.max_length, add_special_tokens=True)["input_ids"]
        return {"ids": torch.tensor(all_ids), "prompt_length": min(len(prompt_ids), len(all_ids) - 1), "reward": float(row["reward"]), "experts": row.get("expert_labels", [])}


def _collate(rows: List[Dict[str, Any]], pad: int) -> Dict[str, Any]:
    width = max(len(row["ids"]) for row in rows)
    ids, attention, action = [], [], []
    for row in rows:
        length = len(row["ids"])
        ids.append(torch.cat((row["ids"], torch.full((width - length,), pad))))
        attention.append(torch.cat((torch.ones(length), torch.zeros(width - length))))
        mask = torch.zeros(width - 1)
        mask[max(0, row["prompt_length"] - 1):length - 1] = 1
        action.append(mask)
    return {"input_ids": torch.stack(ids).long(), "attention_mask": torch.stack(attention).long(), "action_mask": torch.stack(action), "rewards": torch.tensor([row["reward"] for row in rows]), "experts": [row["experts"] for row in rows]}


def _statistics(model: CMoECausalLM, batch: Mapping[str, Any], no_grad: bool = False, communication: bool = True) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    context = torch.no_grad() if no_grad else torch.enable_grad()
    with context:
        output = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"], expert_labels=batch["experts"], communication=communication, output_hidden_states=True)
        logits = output.logits[:, :-1]
        targets = batch["input_ids"][:, 1:]
        distribution = torch.distributions.Categorical(logits=logits)
        log_probs = distribution.log_prob(targets)
        entropy = distribution.entropy()
        values = model.value_head(output.hidden_states[-1][:, :-1]).squeeze(-1) if model.value_head is not None else torch.zeros_like(log_probs)
    return log_probs, values, entropy


def train_ppo(config: Mapping[str, Any], rollouts: str, output_dir: str, initial_adapters: Optional[str] = None) -> Dict[str, Any]:
    model, tokenizer, replaced = load_model(config)
    reference, _, _ = load_model(config)
    if initial_adapters:
        model.load_adapters(initial_adapters); reference.load_adapters(initial_adapters)
    hidden_size = int(getattr(model.base_model.config, "hidden_size"))
    model.add_value_head(hidden_size)
    reference.add_value_head(hidden_size)
    reference.load_state_dict(model.state_dict(), strict=False)
    for parameter in reference.parameters():
        parameter.requires_grad_(False)
    experiment = config.get("experiment", {})
    active = EXPERT_CATEGORIES if experiment.get("moe", True) else []
    communication = bool(experiment.get("lora", True) and (not experiment.get("moe", True) or experiment.get("communication", True)))
    freeze_for_stage(model, "ppo", active, communication)
    settings = config["ppo"]
    dataset = RolloutDataset(rollouts, tokenizer, int(config["model"]["sequence_length"]), config.get("profile") == "paper", int(settings["candidates"]))
    loader = DataLoader(dataset, batch_size=int(settings["batch_size"]), shuffle=True, collate_fn=lambda rows: _collate(rows, tokenizer.pad_token_id))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device); reference.to(device)
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=float(settings["learning_rate"]), betas=tuple(config["optimizer"]["betas"]), eps=float(config["optimizer"]["eps"]), weight_decay=float(config["optimizer"]["weight_decay"]))
    metrics: List[Dict[str, float]] = []
    for batch in loader:
        batch = {key: (value.to(device) if torch.is_tensor(value) else value) for key, value in batch.items()}
        with torch.no_grad():
            old_log_probs, _, _ = _statistics(model, batch, no_grad=True, communication=communication)
            reference_log_probs, _, _ = _statistics(reference, batch, no_grad=True, communication=communication)
        returns = terminal_returns(batch["rewards"], batch["action_mask"].shape[1], float(settings["gamma"]))
        for _ in range(int(settings["epochs"])):
            log_probs, values, entropy = _statistics(model, batch, communication=communication)
            loss, detail = ppo_loss(log_probs, old_log_probs, reference_log_probs, values, returns, entropy, batch["action_mask"], float(settings["clip"]), float(settings["value_coefficient"]), float(settings["kl_coefficient"]), float(settings["entropy_coefficient"]))
            optimizer.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], float(config["optimizer"]["gradient_clip"]))
            optimizer.step()
            metrics.append({"loss": float(loss.detach().cpu()), **detail})
    model.save_adapters(output_dir, {"stage": "ppo", "base_model": config["model"]["name"], "target_modules": replaced, "rollouts": str(rollouts)})
    write_json(Path(output_dir) / "training_metrics.json", metrics)
    return {"updates": len(metrics), "output_dir": output_dir, "last": metrics[-1] if metrics else {}}
