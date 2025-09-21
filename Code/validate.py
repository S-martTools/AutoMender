import argparse, json, pathlib, yaml
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
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--orig", required=True); ap.add_argument("--patched", required=True)
    ap.add_argument("--weights", required=True); ap.add_argument("--report", required=True)
    ap.add_argument("--config", default="Code/config/default.yaml"); args=ap.parse_args()
    cfg=yaml.safe_load(pathlib.Path(args.config).read_text(encoding="utf-8")) if pathlib.Path(args.config).exists() else {}
    detectors=[SmartFastDetector(),SlitherDetector(),SecurifyDetector(),RSymXDetector(),ILFDetector(),VulHunterDetector()]
    pre=[d.run(args.orig) for d in detectors]; post=[d.run(args.patched) for d in detectors]
    pre_scores=aggregate(pre, args.weights); post_scores=aggregate(post, args.weights)
    comp_ok=compile_ok(cfg.get("solc_path","solc"), args.patched); sym_ok=symexec_ok(args.orig, args.patched)
    orig_text=pathlib.Path(args.orig).read_text(encoding="utf-8", errors="ignore")
    patched_text=pathlib.Path(args.patched).read_text(encoding="utf-8", errors="ignore")
    gs=gas_struct_score(orig_text, patched_text, cfg.get("gas_similarity",{}).get("leven_threshold", 0.4))
    report={"scores_pre":pre_scores,"scores_post":post_scores,"compile_ok":comp_ok,"symexec_ok":sym_ok,"gas_struct_score":gs}
    pathlib.Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2)); print(json.dumps(report, ensure_ascii=False, indent=2))
if __name__ == "__main__": main()
