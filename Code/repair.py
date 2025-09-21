import argparse, json, pathlib, yaml
from core.rag import build_prompt
from core.cot import plan, extract_patch
from core.registry import get_patch_generator
from core.detectors.smartfast import SmartFastDetector
from core.detectors.slither import SlitherDetector
from core.detectors.securify import SecurifyDetector
from core.detectors.rsymx import RSymXDetector
from core.detectors.ilf import ILFDetector
from core.detectors.vulhunter import VulHunterDetector
from core.detectors.aggregator import aggregate
from core.validate.compile_check import compile_ok
from core.validate.gas_similarity import gas_struct_score
from core.validate.symexec_check import symexec_ok

def run_pipeline(input_json: str, weights_yaml: str, experts: str, patched_out: str, config_yaml: str):
    data=json.loads(pathlib.Path(input_json).read_text(encoding="utf-8"))
    cfg=yaml.safe_load(pathlib.Path(config_yaml).read_text(encoding="utf-8")) if pathlib.Path(config_yaml).exists() else {}
    detectors=[SmartFastDetector(),SlitherDetector(),SecurifyDetector(),RSymXDetector(),ILFDetector(),VulHunterDetector()]
    pre=[d.run(data["path"]) for d in detectors]
    bug_scores=aggregate(pre, weights_yaml);
    bug_types=[k for k,v in bug_scores.items() if v>0]
    prompt=build_prompt(data["text"], [{"type":t,"detail":"detected by ensemble"} for t in bug_types], knowledge=[])
    prompt=plan(bug_types)+"\n"+prompt

    gen = get_patch_generator()
    raw_out = gen(prompt, experts=experts, config_path="Code/config/moe_lora.yaml")

    patch_code=extract_patch(raw_out)
    patched_path=pathlib.Path(patched_out);
    patched_path.parent.mkdir(parents=True, exist_ok=True)
    
    orig_text=data["text"];
    patched_text=orig_text+"\n\n"+patch_code+"\n";
    patched_path.write_text(patched_text, encoding="utf-8")
    comp_ok=compile_ok(cfg.get("solc_path","solc"), str(patched_path))
    sym_ok=symexec_ok(data["path"], str(patched_path))
    gs=gas_struct_score(orig_text, patched_text, cfg.get("gas_similarity",{}).get("leven_threshold", 0.4))
    post=[d.run(str(patched_path)) for d in detectors]; post_scores=aggregate(post, weights_yaml)

    return {"detector_pre":pre,"detector_post":post,"scores_pre":bug_scores,"scores_post":post_scores,
            "compile_ok":comp_ok,"symexec_ok":sym_ok,"gas_struct_score":gs,"patched_path":str(patched_path),
            "prompt":prompt,"generated":raw_out}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True); ap.add_argument("--experts", default="")
    ap.add_argument("--patched", required=True); ap.add_argument("--weights", default="../Detection_weights/default.yaml")
    ap.add_argument("--config", default="Code/config/default.yaml"); args=ap.parse_args()
    result=run_pipeline(args.input, args.weights, args.experts, args.patched, args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()