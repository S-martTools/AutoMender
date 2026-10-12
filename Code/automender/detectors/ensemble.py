from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import yaml

from ..types import DetectionRun, Finding
from .base import Detector


def load_detector_weights(path: str) -> Dict[str, Dict[str, Dict[str, float]]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    return value.get("tools", value)


class DetectorEnsemble:
    def __init__(self, detectors: Sequence[Detector], weights: Mapping[str, Any], strict: bool = True):
        self.detectors, self.weights, self.strict = list(detectors), dict(weights), strict

    def detect(self, contract_path: str) -> Tuple[List[Finding], List[DetectionRun], Dict[str, float]]:
        runs = [detector.run(contract_path) for detector in self.detectors]
        if self.strict:
            failed = [run.tool + ":" + run.status for run in runs if run.status != "success"]
            if failed:
                raise RuntimeError("Paper detector profile incomplete: " + ", ".join(failed))
        candidates: Dict[str, Finding] = {}
        for run in runs:
            if run.status == "success":
                for finding in run.findings:
                    if not any(_same_segment(existing, finding) for existing in candidates.values()):
                        candidates[finding.segment_key] = finding
        scores: Dict[str, float] = {}
        accepted: List[Finding] = []
        for key, candidate in candidates.items():
            score = 0.0
            for run in runs:
                settings = self.weights.get(run.tool, {}).get(candidate.bug_type)
                if run.status != "success" or not settings:
                    continue
                reported = any(_same_segment(f, candidate) for f in run.findings)
                score += float(settings.get("reported" if reported else "not_reported", 0.0))
            scores[key] = score
            if score > 0:
                accepted.append(candidate)
        return accepted, runs, scores


def _same_segment(left: Finding, right: Finding) -> bool:
    if left.bug_type != right.bug_type:
        return False
    if left.function and right.function:
        return left.function == right.function
    if left.line_start and right.line_start:
        return max(left.line_start, right.line_start) <= min(left.line_end or left.line_start, right.line_end or right.line_start)
    return bool(left.code and right.code and left.code.strip() == right.code.strip()) or left.segment_key == right.segment_key
