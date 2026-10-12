from __future__ import annotations

import copy
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import yaml

from ..utils import write_json
from .matrix import experiment_matrix


def run_ablation_matrix(config: Mapping[str, Any], output_dir: str, command_template: str) -> Dict[str, Any]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for specification in experiment_matrix():
        run_dir = root / specification["run_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        run_config = copy.deepcopy(dict(config))
        run_config["seed"] = specification["seed"]
        run_config["cmoe"]["lambda_comm"] = 1.0 if specification["communication"] else 0.0
        run_config["cmoe"]["conflict_alpha"] = 0.1 if specification["conflict"] else 0.0
        run_config["quality"]["distance"] = specification["distance"]
        run_config["experiment"] = specification
        config_path = run_dir / "config.yaml"
        config_path.write_text(yaml.safe_dump(run_config, sort_keys=False), encoding="utf-8")
        values = {**specification, "config": str(config_path), "run_dir": str(run_dir)}
        command = [part.format(**values) for part in shlex.split(command_template)]
        process = subprocess.run(command, capture_output=True, text=True)
        record = {"specification": specification, "command": command, "exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr}
        write_json(run_dir / "orchestration.json", record)
        results.append(record)
    summary = {"runs": len(results), "successful": sum(item["exit_code"] == 0 for item in results), "results": results}
    write_json(root / "ablation_summary.json", summary)
    return summary
