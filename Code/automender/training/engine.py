from __future__ import annotations

import json
import math
import os
import platform
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence

import torch
from torch.utils.data import DataLoader, IterableDataset

from ..models.cmoe_lora import CMoECausalLM, freeze_for_stage, inject_cmoe_lora
from ..taxonomy import EXPERT_CATEGORIES
from ..utils import git_state, iter_files, read_jsonl, set_seed, write_json
from .losses import conflict_regularization, incremental_communication_regularization


def load_model(config: Mapping[str, Any]) -> tuple:
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as error:
        raise RuntimeError("Training requires transformers; install requirements-train.txt") from error
    model_name = config["paths"].get("model_path") or config["model"]["name"]
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = getattr(torch, config["model"].get("dtype", "bfloat16"), torch.float32)
    base = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype, trust_remote_code=True)
    for parameter in base.parameters():
        parameter.requires_grad_(False)
    cmoe = config["cmoe"]
    replaced = inject_cmoe_lora(base, config["model"]["target_modules"], cmoe["rank"], cmoe["alpha"], cmoe["dropout"], cmoe["lambda_comm"])
    return CMoECausalLM(base), tokenizer, replaced


class CausalTextDataset(IterableDataset):
    def __init__(self, paths: Sequence[Path], tokenizer: Any, sequence_length: int):
        self.paths, self.tokenizer, self.sequence_length = list(paths), tokenizer, sequence_length

    def __iter__(self):
        for path in self.paths:
            text = path.read_text(encoding="utf-8", errors="replace")
            tokens = self.tokenizer(text, truncation=True, max_length=self.sequence_length, add_special_tokens=True)["input_ids"]
            if len(tokens) > 1:
                tensor = torch.tensor(tokens, dtype=torch.long)
                yield {"input_ids": tensor, "labels": tensor.clone(), "expert_labels": []}


class RepairDataset(IterableDataset):
    def __init__(self, jsonl: str, tokenizer: Any, sequence_length: int, split: str = "train", required_expert: Optional[str] = None):
        self.jsonl, self.tokenizer, self.sequence_length, self.split, self.required_expert = jsonl, tokenizer, sequence_length, split, required_expert

    def __iter__(self):
        for row in read_jsonl(self.jsonl):
            if row.get("split", "train") != self.split:
                continue
            if self.required_expert and self.required_expert not in row.get("expert_labels", []):
                continue
            prompt = repair_training_prompt(row["vulnerable"], row.get("bug_types", []))
            completion = "<repaired_contract>\n%s\n</repaired_contract>\n<repair_rationale>Training reference repair.</repair_rationale>" % row["fixed"]
            prompt_ids = self.tokenizer(prompt, add_special_tokens=True)["input_ids"]
            full = self.tokenizer(prompt + completion, truncation=True, max_length=self.sequence_length, add_special_tokens=True)["input_ids"]
            labels = [-100] * min(len(prompt_ids), len(full)) + full[len(prompt_ids):]
            yield {"input_ids": torch.tensor(full), "labels": torch.tensor(labels), "expert_labels": row.get("expert_labels", [])}


def repair_training_prompt(contract: str, bug_types: Sequence[str]) -> str:
    return (
        "Repair the Solidity contract for these detected bug types: %s.\n"
        "Return the complete contract inside <repaired_contract> and reasoning inside <repair_rationale>.\n"
        "Contract:\n%s\n" % (", ".join(bug_types) or "unknown", contract)
    )


def collate(items: List[Dict[str, Any]], pad_token_id: int) -> Dict[str, Any]:
    width = max(len(item["input_ids"]) for item in items)
    inputs, labels, masks = [], [], []
    for item in items:
        padding = width - len(item["input_ids"])
        inputs.append(torch.cat((item["input_ids"], torch.full((padding,), pad_token_id))))
        labels.append(torch.cat((item["labels"], torch.full((padding,), -100))))
        masks.append(torch.cat((torch.ones(len(item["input_ids"])), torch.zeros(padding))))
    return {"input_ids": torch.stack(inputs).long(), "labels": torch.stack(labels).long(), "attention_mask": torch.stack(masks).long(), "expert_labels": [item["expert_labels"] for item in items]}


def _train(config: Mapping[str, Any], stage: str, dataset: IterableDataset, dataset_size: int, output_dir: str, replaced: Sequence[str], model: CMoECausalLM, tokenizer: Any, active_experts: Sequence[str] = EXPERT_CATEGORIES, reference_gradients: Optional[Mapping[str, torch.Tensor]] = None, reg_alpha: float = 1.0, save_gradients: Optional[str] = None, communication_enabled: bool = True) -> Dict[str, Any]:
    try:
        from accelerate import Accelerator
        from transformers import get_linear_schedule_with_warmup
    except ImportError as error:
        raise RuntimeError("Training requires accelerate and transformers") from error
    settings = config[stage]
    if dataset_size <= 0:
        raise ValueError("No training samples selected for %s" % stage)
    micro_batch = int(settings.get("micro_batch_size", 1))
    accumulation = max(1, int(settings["effective_batch_size"]) // micro_batch)
    freeze_for_stage(model, stage, active_experts, communication_enabled)
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=float(settings["learning_rate"]), betas=tuple(config["optimizer"]["betas"]), eps=float(config["optimizer"]["eps"]), weight_decay=float(config["optimizer"]["weight_decay"]))
    loader = DataLoader(dataset, batch_size=micro_batch, collate_fn=lambda rows: collate(rows, tokenizer.pad_token_id))
    optimizer_steps = max(1, math.ceil(dataset_size * int(settings["epochs"]) / int(settings["effective_batch_size"])))
    scheduler = get_linear_schedule_with_warmup(optimizer, int(optimizer_steps * config["optimizer"]["warmup_ratio"]), optimizer_steps)
    accelerator = Accelerator(gradient_accumulation_steps=accumulation)
    model, optimizer, loader, scheduler = accelerator.prepare(model, optimizer, loader, scheduler)
    metrics: List[Dict[str, float]] = []
    gradient_sums: Dict[str, torch.Tensor] = {}
    gradient_count = 0
    step = 0
    for epoch in range(int(settings["epochs"])):
        for batch in loader:
            with accelerator.accumulate(model):
                expert_labels = batch.pop("expert_labels")
                output = model(**batch, expert_labels=expert_labels, communication=communication_enabled)
                repair_loss = output.loss
                conflict = repair_loss.new_zeros(())
                regularization = repair_loss.new_zeros(())
                conflict_metrics = {"mean_cosine": 0.0, "conflict_rate": 0.0}
                conflict_routes = [[label for label in labels if label in active_experts] for labels in expert_labels]
                if stage == "sft" and any(len(labels) > 1 for labels in conflict_routes):
                    conflict, conflict_metrics = conflict_regularization(repair_loss, accelerator.unwrap_model(model), conflict_routes)
                unwrapped = accelerator.unwrap_model(model)
                if reference_gradients:
                    regularization = incremental_communication_regularization(repair_loss, unwrapped, reference_gradients)
                if save_gradients:
                    named = [(name, parameter) for name, parameter in unwrapped.named_parameters() if ".communication." in name and parameter.requires_grad]
                    gradients = torch.autograd.grad(repair_loss, [parameter for _, parameter in named], retain_graph=True, allow_unused=True)
                    for (name, _), gradient in zip(named, gradients):
                        if gradient is not None:
                            gradient_sums[name] = gradient_sums.get(name, torch.zeros_like(gradient, device="cpu")) + gradient.detach().cpu()
                    gradient_count += 1
                loss = repair_loss + float(config["cmoe"]["conflict_alpha"]) * conflict + reg_alpha * regularization
                accelerator.backward(loss)
                if accelerator.sync_gradients:
                    accelerator.clip_grad_norm_(parameters, float(config["optimizer"]["gradient_clip"]))
                optimizer.step(); scheduler.step(); optimizer.zero_grad()
            step += 1
            metrics.append({"step": step, "loss": float(loss.detach().cpu()), "incremental_reg": float(regularization.detach().cpu()), **conflict_metrics})
    accelerator.wait_for_everyone()
    unwrapped = accelerator.unwrap_model(model)
    if accelerator.is_main_process:
        unwrapped.save_adapters(output_dir, {"stage": stage, "base_model": config["model"]["name"], "target_modules": list(replaced)})
        write_json(Path(output_dir) / "training_metrics.json", metrics)
        if save_gradients and gradient_count:
            Path(save_gradients).parent.mkdir(parents=True, exist_ok=True)
            torch.save({name: value / gradient_count for name, value in gradient_sums.items()}, save_gradients)
    return {"micro_steps": step, "optimizer_steps": optimizer_steps, "output_dir": output_dir, "last": metrics[-1] if metrics else {}}


def train_dapt(config: Mapping[str, Any], output_dir: str) -> Dict[str, Any]:
    model, tokenizer, replaced = load_model(config)
    paths = list(iter_files(config["paths"]["semantic_dir"], ".sol"))
    dataset = CausalTextDataset(paths, tokenizer, int(config["model"]["sequence_length"]))
    return _train(config, "dapt", dataset, len(paths), output_dir, replaced, model, tokenizer)


def train_sft(config: Mapping[str, Any], samples_jsonl: str, output_dir: str, initial_adapters: Optional[str] = None, new_category: Optional[str] = None, reference_gradients_path: Optional[str] = None, reg_alpha: float = 1.0, save_gradients: Optional[str] = None) -> Dict[str, Any]:
    model, tokenizer, replaced = load_model(config)
    if initial_adapters:
        model.load_adapters(initial_adapters)
    if new_category and new_category not in EXPERT_CATEGORIES:
        raise ValueError("Unknown expert category: %s" % new_category)
    dataset = RepairDataset(samples_jsonl, tokenizer, int(config["model"]["sequence_length"]), required_expert=new_category)
    size = sum(1 for row in read_jsonl(samples_jsonl) if row.get("split", "train") == "train" and (not new_category or new_category in row.get("expert_labels", [])))
    references = torch.load(reference_gradients_path, map_location="cpu") if reference_gradients_path else None
    experiment = config.get("experiment", {})
    active = [new_category] if new_category else (EXPERT_CATEGORIES if experiment.get("moe", True) else [])
    communication = True if new_category else bool(experiment.get("lora", True) and (not experiment.get("moe", True) or experiment.get("communication", True)))
    if not active and not communication:
        raise ValueError("SFT configuration has no trainable adapter")
    return _train(config, "sft", dataset, size, output_dir, replaced, model, tokenizer, active, references, reg_alpha, save_gradients, communication)


def write_run_manifest(config: Mapping[str, Any], output_dir: str, command: str, data_fingerprints: Optional[Mapping[str, Any]] = None, checkpoint_lineage: Sequence[str] = ()) -> None:
    try:
        import importlib.metadata as metadata
        packages = {name: metadata.version(name) for name in ("torch", "transformers", "accelerate", "pyyaml") if _has_package(name)}
    except Exception:
        packages = {}
    from ..doctor import diagnose, external_tool_versions
    write_json(Path(output_dir) / "run_manifest.json", {
        "command": command, "config": dict(config), "git": git_state(Path(__file__).parents[3]),
        "python": platform.python_version(), "packages": packages,
        "seed": config.get("seed"), "data_fingerprints": dict(data_fingerprints or {}),
        "paper_eligible": diagnose(config)["paper_ready"],
        "external_tool_versions": external_tool_versions(config),
        "checkpoint_lineage": list(checkpoint_lineage),
    })


def _has_package(name: str) -> bool:
    try:
        import importlib.metadata as metadata
        metadata.version(name)
        return True
    except Exception:
        return False
