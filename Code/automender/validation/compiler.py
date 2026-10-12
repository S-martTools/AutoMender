from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence


PRAGMA_RE = re.compile(r"pragma\s+solidity\s+([^;]+);")
VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")
GAS_RE = re.compile(r"^\s*(?:[A-Za-z_$][\w$]*(?:\([^)]*\))?|\d+\s*\+\s*\d+)\s*(?:=|:)\s*(\d+)\s*$", re.MULTILINE)


@dataclass
class CompileResult:
    status: str
    ok: bool
    version: str = ""
    gas: Optional[int] = None
    runtime_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""


def pragma_version(text: str) -> str:
    match = PRAGMA_RE.search(text)
    if not match:
        return ""
    versions = VERSION_RE.findall(match.group(1))
    return versions[0] if versions else ""


class SolidityCompiler:
    def __init__(self, executable: str = "solc", timeout: int = 120, select_versions: bool = True):
        self.executable, self.timeout, self.select_versions = executable, timeout, select_versions

    def compile(self, contract_path: str, version: str = "") -> CompileResult:
        if not (Path(self.executable).exists() or shutil.which(self.executable)):
            return CompileResult(status="unavailable", ok=False, stderr="solc executable not found")
        source = Path(contract_path).read_text(encoding="utf-8", errors="replace")
        selected = version or pragma_version(source)
        if selected and self.select_versions and shutil.which("solc-select"):
            use = subprocess.run(["solc-select", "use", selected], capture_output=True, text=True)
            if use.returncode != 0:
                return CompileResult(status="unavailable", ok=False, version=selected, stderr=use.stderr or use.stdout)
        start = time.monotonic()
        try:
            process = subprocess.run([self.executable, "--optimize", "--gas", "--bin", contract_path], capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired as error:
            return CompileResult(status="timeout", ok=False, version=selected, runtime_seconds=time.monotonic() - start, stderr=str(error))
        combined = process.stdout + "\n" + process.stderr
        gas_values = [int(value) for value in GAS_RE.findall(combined)]
        return CompileResult(
            status="success" if process.returncode == 0 else "error", ok=process.returncode == 0,
            version=selected, gas=sum(gas_values) if gas_values else None,
            runtime_seconds=time.monotonic() - start, stdout=process.stdout, stderr=process.stderr,
        )
