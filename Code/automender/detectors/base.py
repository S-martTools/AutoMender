from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..taxonomy import normalize_bug_type
from ..types import DetectionRun, Finding


class Detector(ABC):
    name = "detector"
    supported_types: Sequence[str] = ()

    @abstractmethod
    def run(self, contract_path: str) -> DetectionRun:
        raise NotImplementedError


def finding_from_mapping(tool: str, value: Mapping[str, Any], default_path: str) -> Finding:
    bug = value.get("bug_type", value.get("type", value.get("id", "")))
    return Finding(
        tool=tool, bug_type=normalize_bug_type(str(bug)), path=str(value.get("path", default_path)),
        line_start=int(value.get("line_start", value.get("line", 0)) or 0),
        line_end=int(value.get("line_end", value.get("line", 0)) or 0),
        code=str(value.get("code", value.get("snippet", ""))), function=str(value.get("function", "")),
        confidence=float(value.get("confidence", 1.0)), evidence=str(value.get("evidence", "")),
    )


class CommandDetector(Detector):
    """Strict JSON adapter for SmartFast, Securify, RSymX, ILF and VulHunter.

    The configured process must emit either a JSON list of findings or
    {"findings": [...]}. Only exit-code zero is a successful negative vote.
    """

    def __init__(self, name: str, command: Sequence[str], supported_types: Sequence[str], timeout: int = 300):
        self.name = name
        self.command = list(command)
        self.supported_types = tuple(supported_types)
        self.timeout = timeout

    def run(self, contract_path: str) -> DetectionRun:
        executable = self.command[0] if self.command else ""
        if not executable or not (Path(executable).exists() or shutil.which(executable)):
            return DetectionRun(tool=self.name, status="unavailable", error="executable not found: %s" % executable, paper_eligible=False)
        argv = [part.replace("{contract}", contract_path) for part in self.command]
        start = time.monotonic()
        try:
            process = subprocess.run(argv, capture_output=True, text=True, timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired as error:
            return DetectionRun(tool=self.name, status="timeout", runtime_seconds=time.monotonic() - start, error=str(error), paper_eligible=False)
        runtime = time.monotonic() - start
        raw = process.stdout or process.stderr
        if process.returncode != 0:
            return DetectionRun(tool=self.name, status="error", runtime_seconds=runtime, raw_artifact=raw, error="exit %d" % process.returncode, paper_eligible=False)
        try:
            payload = json.loads(process.stdout or "{}")
            rows = payload if isinstance(payload, list) else payload.get("findings", [])
            findings = [finding_from_mapping(self.name, row, contract_path) for row in rows]
        except (ValueError, TypeError, KeyError) as error:
            return DetectionRun(tool=self.name, status="error", runtime_seconds=runtime, raw_artifact=raw, error="invalid JSON schema: %s" % error, paper_eligible=False)
        return DetectionRun(tool=self.name, status="success", findings=findings, runtime_seconds=runtime, raw_artifact=raw)


class FakeDetector(Detector):
    def __init__(self, name: str, findings: Sequence[Finding] = (), supported_types: Sequence[str] = (), status: str = "success"):
        self.name, self._findings, self.supported_types, self.status = name, list(findings), tuple(supported_types), status

    def run(self, contract_path: str) -> DetectionRun:
        return DetectionRun(tool=self.name, status=self.status, findings=self._findings if self.status == "success" else [], paper_eligible=False)
