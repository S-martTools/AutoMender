from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional, Union


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_files(root: Union[str, Path], suffix: Optional[str] = None) -> Iterator[Path]:
    base = Path(root)
    for directory, dirs, files in os.walk(base):
        dirs.sort()
        files.sort()
        for name in files:
            path = Path(directory) / name
            if path.is_file() and (suffix is None or path.suffix.lower() == suffix.lower()):
                yield path


def write_json(path: Union[str, Path], value: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if is_dataclass(value):
        value = asdict(value)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Union[str, Path], rows: Iterable[Dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Union[str, Path]) -> Iterator[Dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def set_seed(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def git_state(root: Union[str, Path]) -> Dict[str, Any]:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--short"], cwd=root, text=True).splitlines()
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": "unknown", "dirty": []}
