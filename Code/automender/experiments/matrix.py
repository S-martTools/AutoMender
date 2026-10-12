from __future__ import annotations

import itertools
import json
import hashlib
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from .metrics import repair_metrics


SYSTEMS = ("base", "lora", "moe_lora", "moe_lora_cot", "moe_lora_cot_rl", "automender")
SEEDS = (42, 3407, 2025)


def experiment_matrix() -> List[Dict[str, Any]]:
    components = {
        "base": {"lora": False, "moe": False, "cot": False, "rl": False, "rag": False},
        "lora": {"lora": True, "moe": False, "cot": False, "rl": False, "rag": False},
        "moe_lora": {"lora": True, "moe": True, "cot": False, "rl": False, "rag": False},
        "moe_lora_cot": {"lora": True, "moe": True, "cot": True, "rl": False, "rag": False},
        "moe_lora_cot_rl": {"lora": True, "moe": True, "cot": True, "rl": True, "rag": False},
        "automender": {"lora": True, "moe": True, "cot": True, "rl": True, "rag": True},
    }
    rows = [{"system": system, "seed": seed, **components[system], "communication": system == "automender", "conflict": system == "automender", "distance": "dtw"} for system, seed in itertools.product(SYSTEMS, SEEDS)]
    rows.extend({"system": "automender", "seed": seed, **components["automender"], "communication": communication, "conflict": conflict, "distance": "dtw"} for seed, communication, conflict in itertools.product(SEEDS, (False, True), (False, True)))
    rows.extend({"system": "automender", "seed": seed, **components["automender"], "communication": True, "conflict": True, "distance": distance} for seed, distance in itertools.product(SEEDS, ("dtw", "levenshtein")))
    unique = {json.dumps(row, sort_keys=True): row for row in rows}
    result = []
    for serialized, row in unique.items():
        result.append({"run_id": hashlib.sha256(serialized.encode()).hexdigest()[:16], **row})
    return result


def summarize_results(path: str) -> Dict[str, Any]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    groups = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "time": 0.0, "peak_gpu_memory": 0.0, "count": 0})
    for row in rows:
        dimensions = {
            "overall": "overall",
            "severity": row.get("severity", "unknown"),
            "bug_type": row.get("bug_type", "unknown"),
            "multi_bug": str(bool(row.get("multi_bug", False))).lower(),
        }
        for dimension, value in dimensions.items():
            key = "%s|seed=%s|%s:%s" % (row.get("system", "unknown"), row.get("seed", "unknown"), dimension, value)
            item = groups[key]
            item["tp"] += int(row.get("tp", 0)); item["fp"] += int(row.get("fp", 0)); item["fn"] += int(row.get("fn", 0))
            item["time"] += float(row.get("runtime_seconds", 0)); item["peak_gpu_memory"] = max(item["peak_gpu_memory"], float(row.get("peak_gpu_memory", 0))); item["count"] += 1
    per_seed = {key: {**repair_metrics(value["tp"], value["fp"], value["fn"]), "mean_time": value["time"] / max(1, value["count"]), "peak_gpu_memory": value["peak_gpu_memory"]} for key, value in groups.items()}
    across = defaultdict(list)
    for key, value in per_seed.items():
        system, _, dimension = key.split("|", 2)
        across[system + "|" + dimension].append(value)
    seed_summary = {}
    for key, values in across.items():
        seed_summary[key] = {}
        for metric in ("iou", "precision", "recall", "f1", "mean_time", "peak_gpu_memory"):
            numbers = [item[metric] for item in values]
            seed_summary[key][metric + "_mean"] = statistics.mean(numbers)
            seed_summary[key][metric + "_std"] = statistics.stdev(numbers) if len(numbers) > 1 else 0.0
    return {"per_seed": per_seed, "seed_summary": seed_summary}
