from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Set, Tuple

from ..utils import iter_files
from .solidity import normalize_text, normalize_tokens


def _digests(path: Path) -> Tuple[str, str, str]:
    raw = path.read_bytes()
    text = normalize_text(raw)
    return (
        hashlib.sha256(raw).hexdigest(),
        hashlib.sha256(text.encode("utf-8")).hexdigest(),
        hashlib.sha256(normalize_tokens(text).encode("utf-8")).hexdigest(),
    )


def build_test_hash_index(test_dirs: Mapping[str, str]) -> Tuple[Dict[str, List[Set[str]]], Dict[str, int]]:
    hashes: Dict[str, List[Set[str]]] = {}
    counts: Dict[str, int] = {}
    for name, root in test_dirs.items():
        buckets = [set(), set(), set()]
        count = 0
        for path in iter_files(root, ".sol"):
            for index, digest in enumerate(_digests(path)):
                buckets[index].add(digest)
            count += 1
        hashes[name] = buckets
        counts[name] = count
    return hashes, counts


def audit_semantic_corpus(
    semantic_dir: str,
    test_dirs: Mapping[str, str],
    expected_files: int = 73391,
    expected_bytes: int = 1075736361,
    strict: bool = True,
    test_index: Any = None,
) -> Dict[str, Any]:
    test_hashes, test_counts = test_index or build_test_hash_index(test_dirs)
    overlaps = {name: {"byte": 0, "text": 0, "token": 0, "examples": []} for name in test_dirs}
    count = 0
    size = 0
    internal = [set(), set(), set()]
    duplicates = [0, 0, 0]
    corpus_fingerprint = hashlib.sha256()
    for path in iter_files(semantic_dir, ".sol"):
        count += 1
        size += path.stat().st_size
        values = _digests(path)
        relative = str(path.relative_to(Path(semantic_dir)))
        corpus_fingerprint.update(relative.encode("utf-8", errors="surrogateescape") + b"\0" + values[0].encode() + b"\n")
        for index, digest in enumerate(values):
            if digest in internal[index]:
                duplicates[index] += 1
            internal[index].add(digest)
        for name, buckets in test_hashes.items():
            labels = ("byte", "text", "token")
            matched = False
            for index, label in enumerate(labels):
                if values[index] in buckets[index]:
                    overlaps[name][label] += 1
                    matched = True
            if matched and len(overlaps[name]["examples"]) < 20:
                overlaps[name]["examples"].append(str(path))
    failures: List[str] = []
    if count != expected_files:
        failures.append("semantic file count %d != %d" % (count, expected_files))
    if size != expected_bytes:
        failures.append("semantic bytes %d != %d" % (size, expected_bytes))
    for name, result in overlaps.items():
        if any(result[key] for key in ("byte", "text", "token")):
            failures.append("whole-contract overlap with %s" % name)
    report = {
        "semantic": {"directory": semantic_dir, "files": count, "bytes": size, "fingerprint": corpus_fingerprint.hexdigest()},
        "expected": {"files": expected_files, "bytes": expected_bytes},
        "test_counts": test_counts,
        "whole_contract_overlap": overlaps,
        "internal_duplicates": dict(zip(("byte", "text", "token"), duplicates)),
        "passed": not failures, "failures": failures,
    }
    if strict and failures:
        raise RuntimeError("Data contamination audit failed: " + "; ".join(failures))
    return report


def audit_pair_duplicates(csv_path: str) -> Dict[str, Any]:
    seen: Set[str] = set()
    vulnerable_seen: Set[str] = set()
    fixed_seen: Set[str] = set()
    duplicates = 0
    vulnerable_reuse = fixed_reuse = 0
    rows = 0
    corpus_fingerprint = hashlib.sha256()
    with Path(csv_path).open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            vulnerable, fixed = _pair_columns(row)
            fingerprint = hashlib.sha256((normalize_tokens(vulnerable) + "\n<PAIR>\n" + normalize_tokens(fixed)).encode()).hexdigest()
            vulnerable_hash = hashlib.sha256(normalize_tokens(vulnerable).encode()).hexdigest()
            fixed_hash = hashlib.sha256(normalize_tokens(fixed).encode()).hexdigest()
            rows += 1
            corpus_fingerprint.update(fingerprint.encode() + b"\n")
            duplicates += int(fingerprint in seen)
            vulnerable_reuse += int(vulnerable_hash in vulnerable_seen)
            fixed_reuse += int(fixed_hash in fixed_seen)
            seen.add(fingerprint)
            vulnerable_seen.add(vulnerable_hash); fixed_seen.add(fixed_hash)
    return {"rows": rows, "unique_pairs": len(seen), "duplicate_pairs": duplicates, "reused_vulnerable_fragments": vulnerable_reuse, "reused_fixed_fragments": fixed_reuse, "fingerprint": corpus_fingerprint.hexdigest(), "internal_only": True, "passed": True}


def audit_pairs_against_tests(csv_path: str, test_dirs: Mapping[str, str], test_index: Any = None) -> Dict[str, Any]:
    """Only a complete vulnerable/fixed sample equal to a complete test contract is contamination."""
    test_hashes, _ = test_index or build_test_hash_index(test_dirs)
    report = {name: {"byte": 0, "text": 0, "token": 0, "examples": []} for name in test_dirs}
    with Path(csv_path).open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        for row_index, row in enumerate(csv.DictReader(handle)):
            vulnerable, fixed = _pair_columns(row)
            for side, value in (("vulnerable", vulnerable), ("fixed", fixed)):
                raw = value.encode("utf-8")
                text = normalize_text(value)
                values = (
                    hashlib.sha256(raw).hexdigest(),
                    hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    hashlib.sha256(normalize_tokens(text).encode("utf-8")).hexdigest(),
                )
                for name, buckets in test_hashes.items():
                    matched = False
                    for index, label in enumerate(("byte", "text", "token")):
                        if values[index] in buckets[index]:
                            report[name][label] += 1
                            matched = True
                    if matched and len(report[name]["examples"]) < 20:
                        report[name]["examples"].append({"row": row_index, "side": side})
    passed = not any(value[label] for value in report.values() for label in ("byte", "text", "token"))
    return {"whole_sample_overlap": report, "passed": passed}


def _pair_columns(row: Mapping[str, str]) -> Tuple[str, str]:
    values = list(row.values())
    vulnerable = row.get("vulnerable") or row.get("defective") or row.get("before") or (values[0] if values else "")
    fixed = row.get("fixed") or row.get("after") or (values[1] if len(values) > 1 else "")
    return vulnerable or "", fixed or ""
