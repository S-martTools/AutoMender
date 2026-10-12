from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence

from ..types import DetectionRun, Finding
from .base import Detector


SLITHER_MAP = {
    "reentrancy-eth": "RE", "reentrancy-no-eth": "REN", "reentrancy-events": "REE",
    "suicidal": "SU", "arbitrary-send": "AS", "unchecked-lowlevel": "UCL",
    "unchecked-send": "UCS", "tx-origin": "TO", "timestamp": "TS",
    "unused-state": "UUS", "costly-loop": "COL", "dead-code": "RDS",
    "boolean-equal": "BE", "constable-states": "CS", "external-function": "EF",
}


class SlitherDetector(Detector):
    name = "Slither"
    supported_types = ("RE", "SU", "AS", "REN", "UCL", "UCS", "TO", "REE", "TS", "UUS", "COL", "RDS", "BE", "CS", "EF")

    def __init__(self, executable: str = "slither", timeout: int = 300):
        self.executable, self.timeout = executable, timeout

    def run(self, contract_path: str) -> DetectionRun:
        if not (Path(self.executable).exists() or shutil.which(self.executable)):
            return DetectionRun(tool=self.name, status="unavailable", error="slither executable not found", paper_eligible=False)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as output:
            output_path = output.name
        start = time.monotonic()
        try:
            process = subprocess.run([self.executable, contract_path, "--json", output_path], capture_output=True, text=True, timeout=self.timeout)
            raw = Path(output_path).read_text(encoding="utf-8", errors="replace") if Path(output_path).exists() else ""
            if process.returncode != 0:
                return DetectionRun(tool=self.name, status="error", runtime_seconds=time.monotonic() - start, raw_artifact=raw or process.stderr, error="exit %d" % process.returncode, paper_eligible=False)
            payload = json.loads(raw)
            findings: List[Finding] = []
            for result in payload.get("results", {}).get("detectors", []):
                bug_type = SLITHER_MAP.get(str(result.get("check", "")).lower())
                if not bug_type:
                    continue
                elements = result.get("elements") or [{}]
                first = elements[0]
                mapping = first.get("source_mapping", {})
                lines = mapping.get("lines") or [0]
                findings.append(Finding(
                    tool=self.name, bug_type=bug_type, path=mapping.get("filename_absolute", contract_path),
                    line_start=min(lines), line_end=max(lines), code=str(first.get("name", "")),
                    function=str(first.get("type_specific_fields", {}).get("parent", {}).get("name", "")),
                    confidence=1.0, evidence=str(result.get("description", "")),
                ))
            return DetectionRun(tool=self.name, status="success", findings=findings, runtime_seconds=time.monotonic() - start, raw_artifact=raw)
        except subprocess.TimeoutExpired as error:
            return DetectionRun(tool=self.name, status="timeout", runtime_seconds=time.monotonic() - start, error=str(error), paper_eligible=False)
        except (OSError, ValueError, TypeError) as error:
            return DetectionRun(tool=self.name, status="error", runtime_seconds=time.monotonic() - start, error=str(error), paper_eligible=False)
        finally:
            Path(output_path).unlink(missing_ok=True) if hasattr(Path(output_path), "unlink") else None
