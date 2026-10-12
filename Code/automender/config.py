from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

import yaml


DEFAULTS: Dict[str, Any] = {
    "profile": "paper",
    "strict": True,
    "seed": 42,
    "model": {
        "name": "Qwen/Qwen2-7B-Instruct",
        "dtype": "bfloat16",
        "device": "auto",
        "sequence_length": 3072,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    },
    "cmoe": {"rank": 8, "alpha": 32.0, "dropout": 0.1, "lambda_comm": 1.0, "conflict_alpha": 0.1},
    "dapt": {"epochs": 1, "learning_rate": 2e-4, "effective_batch_size": 32},
    "sft": {"epochs": 3, "learning_rate": 2e-4, "effective_batch_size": 32},
    "optimizer": {
        "betas": [0.9, 0.999], "eps": 1e-8, "weight_decay": 0.0,
        "warmup_ratio": 0.03, "gradient_clip": 1.0,
    },
    "ppo": {
        "candidates": 4, "clip": 0.2, "gamma": 1.0, "value_coefficient": 0.5,
        "kl_coefficient": 0.01, "entropy_coefficient": 0.01, "epochs": 4,
        "batch_size": 32, "learning_rate": 1e-5,
    },
    "quality": {
        "lambda_old": 1.0, "lambda_new": 1.0, "lambda_change": 0.5,
        "invalid_penalty": 10000.0, "stopping_threshold": 5000.0,
        "distance": "dtw",
    },
    "repair": {"max_iterations": 3, "max_new_tokens": 3072},
    "paths": {},
    "detectors": {},
}

ENV_PATHS = {
    "AUTOMENDER_SEMANTIC_DIR": "semantic_dir",
    "AUTOMENDER_PAIRS_CSV": "pairs_csv",
    "AUTOMENDER_TEST1_DIR": "dataset1_dir",
    "AUTOMENDER_TEST2_DIR": "dataset2_dir",
    "AUTOMENDER_TEST3_DIR": "dataset3_dir",
    "AUTOMENDER_OUTPUT_DIR": "output_dir",
    "AUTOMENDER_MODEL": "model_path",
}


def _merge(base: Dict[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: Optional[Union[str, Path]] = None, overrides: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    config = copy.deepcopy(DEFAULTS)
    if path:
        config_path = Path(path).resolve()
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        parent = loaded.pop("extends", None)
        if parent:
            with (config_path.parent / parent).open("r", encoding="utf-8") as handle:
                _merge(config, yaml.safe_load(handle) or {})
        _merge(config, loaded)
    if overrides:
        _merge(config, overrides)
    for env_name, key in ENV_PATHS.items():
        if os.getenv(env_name):
            config.setdefault("paths", {})[key] = os.environ[env_name]
    weights = config.get("detectors", {}).get("weights")
    if weights and not Path(weights).is_absolute() and not Path(weights).exists():
        repository_relative = Path(__file__).resolve().parents[2] / weights
        if repository_relative.exists():
            config["detectors"]["weights"] = str(repository_relative)
    return config


def require_paths(config: Mapping[str, Any], *names: str) -> None:
    missing = [name for name in names if not config.get("paths", {}).get(name)]
    if missing:
        envs = {value: key for key, value in ENV_PATHS.items()}
        hints = ", ".join(f"{name} ({envs.get(name, 'CLI/config')})" for name in missing)
        raise ValueError(f"Missing required paths: {hints}")
