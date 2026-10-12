from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from .config import load_config, require_paths
from .data.audit import audit_pair_duplicates, audit_pairs_against_tests, audit_semantic_corpus, build_test_hash_index
from .data.labeling import label_pairs
from .data.prepare import prepare_semantic
from .detectors.base import CommandDetector
from .detectors.ensemble import DetectorEnsemble, load_detector_weights
from .detectors.slither import SlitherDetector
from .doctor import diagnose
from .experiments.matrix import experiment_matrix, summarize_results
from .knowledge.index import KnowledgeIndex, build_index
from .utils import write_json
from .validation.behavior import BehaviorValidator
from .validation.compiler import SolidityCompiler
from .validation.quality import evaluate_quality


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _detectors(config: Mapping[str, Any]) -> DetectorEnsemble:
    detector_config = config.get("detectors", {})
    weights = load_detector_weights(detector_config.get("weights", "Detection_weights/default.yaml"))
    instances = []
    for name, settings in detector_config.get("tools", {}).items():
        if name.lower() == "slither":
            command = settings.get("command", ["slither"])
            instances.append(SlitherDetector(command[0], int(settings.get("timeout", 300))))
        else:
            instances.append(CommandDetector(name, settings.get("command", []), settings.get("supported_types", []), int(settings.get("timeout", 300))))
    return DetectorEnsemble(instances, weights, bool(config.get("strict", True)))


def _audit(config: Mapping[str, Any], strict: bool) -> Dict[str, Any]:
    require_paths(config, "semantic_dir", "dataset1_dir", "dataset2_dir", "dataset3_dir")
    paths = config["paths"]
    test_dirs = {"Dataset1": paths["dataset1_dir"], "Dataset2": paths["dataset2_dir"], "Dataset3": paths["dataset3_dir"]}
    test_index = build_test_hash_index(test_dirs)
    report = audit_semantic_corpus(paths["semantic_dir"], test_dirs, strict=False, test_index=test_index)
    if paths.get("pairs_csv"):
        report["paired"] = audit_pair_duplicates(paths["pairs_csv"])
        contamination = audit_pairs_against_tests(paths["pairs_csv"], test_dirs, test_index=test_index)
        report["paired_test_contamination"] = contamination
        if not contamination["passed"]:
            report["passed"] = False; report["failures"].append("complete paired sample overlaps a complete test contract")
    return report


def _require_audit(config: Mapping[str, Any]) -> Dict[str, Any]:
    report = _audit(config, False)
    if not report["passed"]:
        raise RuntimeError("Data audit failed: " + "; ".join(report["failures"]))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="automender", description="Paper-grade AutoMender artifact")
    parser.add_argument("--config", default=str(Path(__file__).parents[1] / "config" / "default.yaml"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    audit = sub.add_parser("audit-data"); audit.add_argument("--output"); audit.add_argument("--no-strict", action="store_true")
    prepare = sub.add_parser("prepare-semantic"); prepare.add_argument("--source"); prepare.add_argument("--output", required=True)
    labels = sub.add_parser("label-pairs"); labels.add_argument("--csv"); labels.add_argument("--manifest"); labels.add_argument("--detector-evidence"); labels.add_argument("--output", required=True)
    index = sub.add_parser("build-index"); index.add_argument("--output", required=True); index.add_argument("--semantic"); index.add_argument("--knowledge-jsonl"); index.add_argument("--bug-description-xlsx")
    dapt = sub.add_parser("train-dapt"); dapt.add_argument("--output", required=True)
    sft = sub.add_parser("train-sft"); sft.add_argument("--samples", required=True); sft.add_argument("--initial-adapters"); sft.add_argument("--new-category"); sft.add_argument("--reference-gradients"); sft.add_argument("--reg-alpha", type=float, default=1.0); sft.add_argument("--save-communication-gradients"); sft.add_argument("--output", required=True)
    ppo = sub.add_parser("train-ppo"); ppo.add_argument("--rollouts", required=True); ppo.add_argument("--initial-adapters", required=True); ppo.add_argument("--output", required=True)
    repair = sub.add_parser("repair"); repair.add_argument("--contract", required=True); repair.add_argument("--validation-manifest", required=True); repair.add_argument("--adapters"); repair.add_argument("--index"); repair.add_argument("--output", required=True); repair.add_argument("--report", required=True)
    validate = sub.add_parser("validate"); validate.add_argument("--original", required=True); validate.add_argument("--repaired", required=True); validate.add_argument("--validation-manifest", required=True); validate.add_argument("--output", required=True)
    evaluate = sub.add_parser("evaluate"); evaluate.add_argument("--results", required=True); evaluate.add_argument("--output")
    ablate = sub.add_parser("ablate"); ablate.add_argument("--output", required=True); ablate.add_argument("--command-template")
    return parser


def main(argv: Sequence[str] = ()) -> int:
    args = build_parser().parse_args(list(argv) if argv else None)
    config = load_config(args.config)
    try:
        if args.command == "doctor":
            result = diagnose(config)
        elif args.command == "audit-data":
            result = _audit(config, False)
            if args.output: write_json(args.output, result)
            if not args.no_strict and not result["passed"]:
                raise RuntimeError("Data audit failed: " + "; ".join(result["failures"]))
        elif args.command == "prepare-semantic":
            source = args.source or config.get("paths", {}).get("semantic_dir")
            if not source: raise ValueError("--source or AUTOMENDER_SEMANTIC_DIR is required")
            result = prepare_semantic(source, args.output)
        elif args.command == "label-pairs":
            csv_path = args.csv or config.get("paths", {}).get("pairs_csv")
            if not csv_path: raise ValueError("--csv or AUTOMENDER_PAIRS_CSV is required")
            result = label_pairs(csv_path, args.output, args.manifest, detector_evidence=args.detector_evidence)
        elif args.command == "build-index":
            result = build_index(args.output, args.semantic or config.get("paths", {}).get("semantic_dir"), args.knowledge_jsonl, args.bug_description_xlsx)
        elif args.command == "train-dapt":
            audit_report = _require_audit(config)
            from .training.engine import train_dapt, write_run_manifest
            result = train_dapt(config, args.output); write_run_manifest(config, args.output, "train-dapt", audit_report)
        elif args.command == "train-sft":
            audit_report = _require_audit(config)
            from .training.engine import train_sft, write_run_manifest
            result = train_sft(config, args.samples, args.output, args.initial_adapters, args.new_category, args.reference_gradients, args.reg_alpha, args.save_communication_gradients); write_run_manifest(config, args.output, "train-sft", audit_report, [args.initial_adapters] if args.initial_adapters else [])
        elif args.command == "train-ppo":
            audit_report = _require_audit(config)
            from .training.online_ppo import train_ppo
            from .training.engine import write_run_manifest
            audit_report["rollouts"] = args.rollouts
            result = train_ppo(config, args.rollouts, args.output, args.initial_adapters); write_run_manifest(config, args.output, "train-ppo", audit_report, [args.initial_adapters])
        elif args.command == "repair":
            from .models.generation import HuggingFaceGenerator
            from .pipeline.repair import IterativeRepairPipeline
            from .training.engine import load_model
            features = config.get("experiment", {"lora": True, "moe": True, "cot": True, "rl": True, "rag": True, "communication": True})
            if features.get("lora", True) and not args.adapters:
                raise ValueError("This experiment requires --adapters")
            if features.get("rag", True) and config.get("strict", True) and not args.index:
                raise ValueError("Strict RAG experiment requires --index")
            model, tokenizer, _ = load_model(config)
            if args.adapters:
                model.load_adapters(args.adapters)
            import torch
            model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu")); model.eval()
            communication_enabled = bool(features.get("lora", True) and (not features.get("moe", True) or features.get("communication", True)))
            generator = HuggingFaceGenerator(model, tokenizer, int(config["repair"]["max_new_tokens"]), communication_enabled)
            behavior = BehaviorValidator(config.get("behavior", {}).get("command", []), int(config.get("behavior", {}).get("timeout", 600)))
            pipeline = IterativeRepairPipeline(generator, _detectors(config), SolidityCompiler(config.get("compiler", {}).get("executable", "solc")), behavior, KnowledgeIndex(args.index) if args.index else None, int(config["repair"]["max_iterations"]), float(config["quality"]["stopping_threshold"]), config["quality"], features)
            repair_result = pipeline.repair(args.contract, args.validation_manifest)
            Path(args.output).write_text(repair_result.final_contract, encoding="utf-8"); write_json(args.report, repair_result.to_dict()); result = repair_result.to_dict()
        elif args.command == "validate":
            original = Path(args.original).read_text(encoding="utf-8", errors="replace"); repaired = Path(args.repaired).read_text(encoding="utf-8", errors="replace")
            ensemble = _detectors(config); before, before_runs, _ = ensemble.detect(args.original); after, after_runs, _ = ensemble.detect(args.repaired)
            compiler = SolidityCompiler(config.get("compiler", {}).get("executable", "solc")); comp_before = compiler.compile(args.original); comp_after = compiler.compile(args.repaired, comp_before.version)
            behavior = BehaviorValidator(config.get("behavior", {}).get("command", [])).validate(args.original, args.repaired, args.validation_manifest)
            quality = evaluate_quality(original, repaired, before, after, comp_after.ok, behavior.ok, comp_before.gas, comp_after.gas, **{key: config["quality"][key] for key in ("lambda_old", "lambda_new", "lambda_change", "invalid_penalty", "distance")})
            result = {"quality": quality.to_dict(), "before": [f.to_dict() for f in before], "after": [f.to_dict() for f in after], "compile_before": comp_before.__dict__, "compile_after": comp_after.__dict__, "behavior": behavior.__dict__, "detector_runs": [r.to_dict() for r in before_runs + after_runs]}; write_json(args.output, result)
        elif args.command == "evaluate":
            result = summarize_results(args.results)
            if args.output: write_json(args.output, result)
        elif args.command == "ablate":
            if args.command_template:
                from .experiments.runner import run_ablation_matrix
                result = run_ablation_matrix(config, args.output, args.command_template)
            else:
                result = {"runs": experiment_matrix(), "note": "Pass --command-template to execute every immutable run; placeholders include {config}, {run_dir}, {system}, {seed}, and {run_id}."}; write_json(args.output, result)
        else:
            raise ValueError("Unknown command")
        _json(result)
        if args.command == "doctor" and config.get("strict", True) and not result["paper_ready"]:
            return 2
        return 0
    except Exception as error:
        print("ERROR: %s" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
