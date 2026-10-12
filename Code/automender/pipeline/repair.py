from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..detectors.ensemble import DetectorEnsemble
from ..knowledge.index import KnowledgeIndex
from ..models.generation import parse_repair_output
from ..taxonomy import experts_for_bug_types
from ..types import Finding, RepairResult
from ..validation.behavior import BehaviorValidator
from ..validation.compiler import SolidityCompiler
from ..validation.quality import evaluate_quality
from .prompt import build_repair_prompt


class IterativeRepairPipeline:
    def __init__(self, generator: Any, detectors: DetectorEnsemble, compiler: SolidityCompiler, behavior: BehaviorValidator, knowledge: Optional[KnowledgeIndex] = None, max_iterations: int = 3, stopping_threshold: float = 5000.0, quality_config: Optional[Dict[str, Any]] = None, features: Optional[Dict[str, bool]] = None):
        self.generator, self.detectors, self.compiler, self.behavior, self.knowledge = generator, detectors, compiler, behavior, knowledge
        self.max_iterations, self.stopping_threshold = max_iterations, stopping_threshold
        self.quality_config = dict(quality_config or {})
        self.features = {"lora": True, "moe": True, "cot": True, "rl": True, "rag": True, **dict(features or {})}

    def repair(self, contract_path: str, validation_manifest: str) -> RepairResult:
        original = Path(contract_path).read_text(encoding="utf-8", errors="replace")
        current, rationale, feedback = original, "", ""
        initial_findings, initial_runs, _ = self.detectors.detect(contract_path)
        paper_eligible = all(run.paper_eligible and run.status == "success" for run in initial_runs)
        current_findings = initial_findings
        original_compile = self.compiler.compile(contract_path)
        best = None
        best_contract, best_rationale = "", ""
        records: List[Dict[str, Any]] = []
        latest_contract = original
        for iteration in range(1, self.max_iterations + 1):
            context = self.knowledge.search(" ".join(f.bug_type for f in current_findings), [f.bug_type for f in current_findings], 5) if self.knowledge and self.features["rag"] else []
            prompt = build_repair_prompt(current, current_findings, context, iteration, feedback, self.features["cot"])
            labels = experts_for_bug_types(f.bug_type for f in current_findings) if self.features["moe"] else []
            output = self.generator.generate(prompt, labels, candidates=1)[0]
            candidate = parse_repair_output(output, iteration)
            latest_contract, rationale = candidate.contract or current, candidate.rationale
            record: Dict[str, Any] = {"iteration": iteration, "candidate": candidate.to_dict()}
            if not candidate.parse_ok or candidate.contract.strip() == current.strip():
                record["invalid_reason"] = "parse failure or empty/no-op full contract"
                records.append(record)
                feedback = record["invalid_reason"]
                continue
            with tempfile.TemporaryDirectory(prefix="automender-repair-") as directory:
                repaired_path = Path(directory) / Path(contract_path).name
                repaired_path.write_text(candidate.contract, encoding="utf-8")
                compile_result = self.compiler.compile(str(repaired_path), version=original_compile.version)
                try:
                    after, detector_runs, scores = self.detectors.detect(str(repaired_path))
                    detector_error = ""
                except RuntimeError as error:
                    after, detector_runs, scores, detector_error = [], [], {}, str(error)
                behavior_result = self.behavior.validate(contract_path, str(repaired_path), validation_manifest) if compile_result.ok else None
                paper_eligible = paper_eligible and compile_result.status == "success" and bool(behavior_result and behavior_result.status == "success") and all(run.paper_eligible and run.status == "success" for run in detector_runs)
                quality = evaluate_quality(
                    original, candidate.contract, initial_findings, after,
                    compile_result.ok and not detector_error, bool(behavior_result and behavior_result.ok),
                    original_compile.gas, compile_result.gas,
                    lambda_old=float(self.quality_config.get("lambda_old", 1.0)),
                    lambda_new=float(self.quality_config.get("lambda_new", 1.0)),
                    lambda_change=float(self.quality_config.get("lambda_change", 0.5)),
                    invalid_penalty=float(self.quality_config.get("invalid_penalty", 10000.0)),
                    distance=str(self.quality_config.get("distance", "dtw")),
                )
                record.update({"compile": compile_result.__dict__, "behavior": behavior_result.__dict__ if behavior_result else None, "detector_runs": [run.to_dict() for run in detector_runs], "vote_scores": scores, "quality": quality.to_dict(), "detector_error": detector_error})
                records.append(record)
                if quality.valid and (best is None or quality.total_cost < best.total_cost):
                    best, best_contract, best_rationale = quality, candidate.contract, candidate.rationale
                current, current_findings = candidate.contract, after
                feedback = "Remaining findings: %s. Compile: %s. Behavior: %s. Cost: %s." % (", ".join(f.bug_type for f in after) or "none", compile_result.status, behavior_result.status if behavior_result else "not-run", quality.total_cost)
                if quality.valid and quality.total_cost < self.stopping_threshold:
                    return RepairResult(contract_path, best_contract, best_rationale, True, "valid_below_threshold", iteration, best, [], records, paper_eligible)
        if best is not None:
            return RepairResult(contract_path, best_contract, best_rationale, True, "best_valid_after_max_iterations", self.max_iterations, best, [], records, paper_eligible)
        return RepairResult(contract_path, latest_contract, rationale, False, "no_valid_candidate", self.max_iterations, None, current_findings, records, paper_eligible)
