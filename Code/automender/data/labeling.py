from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from ..taxonomy import BUG_TO_EXPERT, EXPERT_CATEGORIES, normalize_bug_type
from ..types import RepairSample
from ..utils import write_json, write_jsonl
from .solidity import normalize_tokens


RULES = {
    "reentrancy": [(r"\.call\s*\{?\s*value", "external value call"), (r"nonReentrant|ReentrancyGuard", "reentrancy guard diff")],
    "arithmetic": [(r"SafeMath|unchecked\s*\{|overflow|underflow", "arithmetic protection diff")],
    "unchecked_calls": [(r"require\s*\([^;]*(?:call|send)|success\s*[,=]", "call result check diff")],
    "optimized_operations": [(r"\bcalldata\b|\bimmutable\b|\bconstant\b|unchecked\s*\{", "optimization diff")],
    "access_control": [(r"onlyOwner|AccessControl|require\s*\([^;]*(?:owner|msg\.sender)", "authorization diff")],
    "transaction_dependence": [(r"tx\.origin|front.?run|commit.?reveal|nonce", "transaction-order diff")],
    "block_dependence": [(r"block\.(?:timestamp|number)|blockhash|prevrandao", "block-value diff")],
}


def _manifest(path: Optional[str]) -> Dict[str, Dict[str, Any]]:
    if not path:
        return {}
    result: Dict[str, Dict[str, Any]] = {}
    source = Path(path)
    if source.suffix.lower() == ".jsonl":
        rows = (json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip())
    elif source.suffix.lower() == ".json":
        value = json.loads(source.read_text(encoding="utf-8"))
        rows = value if isinstance(value, list) else value.values()
    else:
        rows = csv.DictReader(source.open("r", encoding="utf-8-sig", newline=""))
    for row in rows:
        key = str(row.get("sample_id", row.get("row", row.get("id", ""))))
        result[key] = dict(row)
    return result


def _columns(row: Mapping[str, str]) -> Tuple[str, str]:
    values = list(row.values())
    before = row.get("vulnerable") or row.get("defective") or row.get("before") or row.get("buggy") or (values[0] if values else "")
    after = row.get("fixed") or row.get("repair") or row.get("after") or row.get("patched") or (values[1] if len(values) > 1 else "")
    return before or "", after or ""


def _explicit_labels(row: Mapping[str, Any]) -> List[str]:
    value = row.get("expert_labels", row.get("bug_types", row.get("labels", "")))
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[,;|]", str(value))
    labels = []
    for item in raw:
        cleaned = str(item).strip().lower().replace(" ", "_").replace("-", "_")
        if cleaned in EXPERT_CATEGORIES:
            category = cleaned
        else:
            normalized = normalize_bug_type(str(item).strip())
            category = BUG_TO_EXPERT.get(normalized, "")
        if category and category not in labels:
            labels.append(category)
    return labels


def _detector_votes(path: Optional[str]) -> Dict[str, Dict[str, set]]:
    votes: Dict[str, Dict[str, set]] = {}
    if not path:
        return votes
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = str(row.get("sample_id", row.get("row", "")))
        tool = str(row.get("tool", "unknown"))
        findings = row.get("findings", row.get("bug_types", []))
        for finding in findings:
            value = finding.get("bug_type", finding.get("type", "")) if isinstance(finding, dict) else finding
            try:
                category = BUG_TO_EXPERT[normalize_bug_type(str(value))]
            except (ValueError, KeyError):
                continue
            votes.setdefault(key, {}).setdefault(category, set()).add(tool)
    return votes


def label_pairs(csv_path: str, output_dir: str, explicit_manifest: Optional[str] = None, validation_fraction: float = 0.05, detector_evidence: Optional[str] = None) -> Dict[str, Any]:
    explicit = _manifest(explicit_manifest)
    detector_votes = _detector_votes(detector_evidence)
    samples: List[RepairSample] = []
    exact_seen = set()
    duplicate_pairs = 0
    with Path(csv_path).open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            vulnerable, fixed = _columns(row)
            fingerprint = hashlib.sha256((normalize_tokens(vulnerable) + "\n<PAIR>\n" + normalize_tokens(fixed)).encode()).hexdigest()
            duplicate_pairs += int(fingerprint in exact_seen)
            exact_seen.add(fingerprint)
            sample_id = fingerprint[:16]
            override = explicit.get(sample_id) or explicit.get(str(index))
            evidence: List[str] = []
            if override:
                labels = _explicit_labels(override)
                selected = list(labels)
                confidence, source = 1.0, "explicit_manifest"
                evidence.append("explicit label manifest")
            else:
                labels = []
                selected = []
                diff_text = "\n".join(line[2:] for line in difflib.ndiff(vulnerable.splitlines(), fixed.splitlines()) if line.startswith("+ "))
                for category, rules in RULES.items():
                    matches = [description for pattern, description in rules if re.search(pattern, diff_text, re.I)]
                    if matches:
                        labels.append(category)
                        selected.append(category)
                        evidence.extend("%s: %s" % (category, match) for match in matches)
                votes = detector_votes.get(sample_id, detector_votes.get(str(index), {}))
                voted = [category for category, tools in votes.items() if len(tools) >= 2]
                for category, tools in votes.items():
                    if category not in labels:
                        labels.append(category)
                    if category in voted and category not in selected:
                        selected.append(category)
                    evidence.append("%s: detector support from %s" % (category, ",".join(sorted(tools))))
                # A precise pattern on an added repair line is both rule and diff evidence.
                confidence = 1.0 if selected else (0.5 if labels else 0.0)
                source = "detector_votes+diff_rules" if votes and diff_text else ("detector_votes" if votes else "diff_rules")
            high = bool(selected)
            split = "validation" if int(fingerprint[:8], 16) / float(0xFFFFFFFF) < validation_fraction else "train"
            samples.append(RepairSample(
                sample_id=sample_id, vulnerable=vulnerable, fixed=fixed,
                bug_types=labels, expert_labels=selected,
                label_source=source if high else source + ":low_confidence",
                label_confidence=confidence, evidence=evidence, split=split,
            ))
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    write_jsonl(target / "repair_samples.jsonl", (sample.to_dict() for sample in samples))
    counts = Counter(label for sample in samples for label in sample.expert_labels)
    sources = Counter(sample.label_source for sample in samples)
    report = {
        "rows": len(samples), "unique_pairs": len(exact_seen), "duplicate_pairs": duplicate_pairs,
        "train": sum(s.split == "train" for s in samples), "validation": sum(s.split == "validation" for s in samples),
        "expert_counts": {name: counts[name] for name in EXPERT_CATEGORIES},
        "communication_only": sum(not s.expert_labels for s in samples),
        "low_confidence_ratio": sum(not s.expert_labels for s in samples) / max(1, len(samples)),
        "multi_label": sum(len(s.expert_labels) > 1 for s in samples), "label_sources": dict(sources),
    }
    write_json(target / "label_report.json", report)
    return report
