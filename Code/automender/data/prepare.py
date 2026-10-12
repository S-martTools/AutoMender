from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Iterator

from ..utils import iter_files, write_json
from .semantics import extract_file
from .solidity import normalize_text, normalize_tokens


def prepare_semantic(source_dir: str, output_dir: str) -> Dict[str, Any]:
    root = Path(source_dir)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    manifest = target / "semantic_manifest.jsonl"
    total_bytes = 0
    count = 0
    with manifest.open("w", encoding="utf-8") as handle:
        for path in iter_files(root, ".sol"):
            raw = path.read_bytes()
            text = normalize_text(raw)
            semantics = extract_file(path)
            row = {
                "path": str(path.relative_to(root)), "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "token_sha256": hashlib.sha256(normalize_tokens(text).encode()).hexdigest(),
                "semantics": semantics.to_dict(),
            }
            import json
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
            total_bytes += len(raw)
    report = {"files": count, "bytes": total_bytes, "manifest": str(manifest)}
    write_json(target / "semantic_report.json", report)
    return report
