from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Mapping


def diagnose(config: Mapping[str, Any]) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}
    version = tuple(int(part) for part in platform.python_version_tuple()[:2])
    checks["python"] = {"ok": version >= (3, 10), "version": platform.python_version(), "required": ">=3.10"}
    for package in ("torch", "transformers", "accelerate", "yaml"):
        checks[package] = {"ok": importlib.util.find_spec(package) is not None}
    try:
        import torch
        checks["gpu"] = {"ok": torch.cuda.is_available(), "count": torch.cuda.device_count() if torch.cuda.is_available() else 0}
    except ImportError:
        checks["gpu"] = {"ok": False, "error": "torch unavailable"}
    solc = config.get("compiler", {}).get("executable", "solc")
    solc_present = bool(shutil.which(solc) or Path(solc).exists())
    solc_output = ""
    solc_ok = False
    if solc_present:
        try:
            process = subprocess.run([solc, "--version"], capture_output=True, text=True, timeout=10)
            solc_output = (process.stdout or process.stderr).strip()
            solc_ok = process.returncode == 0 and "Version" in solc_output
        except (OSError, subprocess.TimeoutExpired) as error:
            solc_output = str(error)
    checks["solc"] = {"ok": solc_ok, "executable": solc, "version_output": solc_output}
    model = config.get("paths", {}).get("model_path") or config.get("model", {}).get("name")
    local_model = bool(model and Path(str(model)).exists())
    cached_model = False
    if model and not local_model and "/" in str(model):
        cached = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + str(model).replace("/", "--"))
        cached_model = cached.exists() and any((cached / "snapshots").glob("*"))
    checks["model"] = {"ok": local_model or cached_model, "identifier": model, "local": local_model, "cached": cached_model}
    for name, settings in config.get("detectors", {}).get("tools", {}).items():
        command = settings.get("command", [])
        executable = command[0] if command else ""
        checks["detector:%s" % name] = {"ok": bool(executable and (shutil.which(executable) or Path(executable).exists())), "executable": executable}
    behavior = config.get("behavior", {}).get("command", [])
    executable = behavior[0] if behavior else ""
    checks["behavior"] = {"ok": bool(executable and (shutil.which(executable) or Path(executable).exists())), "executable": executable}
    required = [key for key in checks if key in ("python", "torch", "transformers", "accelerate", "gpu", "solc", "model", "behavior") or key.startswith("detector:")]
    return {"paper_ready": all(checks[key].get("ok", False) for key in required), "checks": checks}


def external_tool_versions(config: Mapping[str, Any]) -> Dict[str, str]:
    commands = {"solc": [config.get("compiler", {}).get("executable", "solc"), "--version"]}
    for name, settings in config.get("detectors", {}).get("tools", {}).items():
        command = settings.get("command", [])
        if command:
            commands[name] = [command[0], "--version"]
    behavior = config.get("behavior", {}).get("command", [])
    if behavior:
        commands["behavior"] = [behavior[0], "--version"]
    versions: Dict[str, str] = {}
    for name, command in commands.items():
        if not (shutil.which(command[0]) or Path(command[0]).exists()):
            versions[name] = "unavailable"
            continue
        try:
            process = subprocess.run(command, capture_output=True, text=True, timeout=10)
            versions[name] = ((process.stdout or process.stderr).strip()[:1000] if process.returncode == 0 else "error: " + (process.stderr or process.stdout).strip()[:900])
        except (OSError, subprocess.TimeoutExpired) as error:
            versions[name] = "error: %s" % error
    return versions
