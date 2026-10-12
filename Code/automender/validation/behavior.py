from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class BehaviorResult:
    status: str
    ok: bool
    cases: List[Dict[str, Any]] = field(default_factory=list)
    runtime_seconds: float = 0.0
    raw: str = ""
    error: str = ""


class BehaviorValidator:
    def __init__(self, command: Sequence[str], timeout: int = 600):
        self.command, self.timeout = list(command), timeout

    def validate(self, original: str, repaired: str, manifest: str) -> BehaviorResult:
        executable = self.command[0] if self.command else ""
        if not executable or not (Path(executable).exists() or shutil.which(executable)):
            return BehaviorResult(status="unavailable", ok=False, error="behavior adapter not found")
        argv = [part.replace("{original}", original).replace("{repaired}", repaired).replace("{manifest}", manifest) for part in self.command]
        start = time.monotonic()
        try:
            process = subprocess.run(argv, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired as error:
            return BehaviorResult(status="timeout", ok=False, runtime_seconds=time.monotonic() - start, error=str(error))
        if process.returncode != 0:
            return BehaviorResult(status="error", ok=False, runtime_seconds=time.monotonic() - start, raw=process.stdout, error=process.stderr)
        try:
            payload = json.loads(process.stdout)
            cases = payload.get("cases", [])
            ok = bool(payload.get("ok", cases and all(bool(case.get("passed")) for case in cases)))
            if not cases:
                raise ValueError("no validation cases returned")
            for case in cases:
                if case.get("oracle") not in ("repair-invariant", "repair-sensitive"):
                    raise ValueError("case has invalid oracle")
            return BehaviorResult(status="success", ok=ok, cases=cases, runtime_seconds=time.monotonic() - start, raw=process.stdout)
        except (ValueError, TypeError) as error:
            return BehaviorResult(status="error", ok=False, runtime_seconds=time.monotonic() - start, raw=process.stdout, error=str(error))
