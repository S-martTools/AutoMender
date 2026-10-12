from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Sequence


class ExternalBaselineAdapter:
    """Adapter only: AutoMender never substitutes or fabricates a baseline implementation."""
    def __init__(self, name: str, command: Sequence[str], timeout: int = 1800):
        self.name, self.command, self.timeout = name, list(command), timeout

    def run(self, contract: str, output: str) -> Dict[str, Any]:
        executable = self.command[0] if self.command else ""
        if not executable or not (Path(executable).exists() or shutil.which(executable)):
            return {"name": self.name, "status": "unavailable", "paper_eligible": False}
        argv = [part.replace("{contract}", contract).replace("{output}", output) for part in self.command]
        process = subprocess.run(argv, capture_output=True, text=True, timeout=self.timeout)
        return {"name": self.name, "status": "success" if process.returncode == 0 else "error", "stdout": process.stdout, "stderr": process.stderr, "paper_eligible": process.returncode == 0}
