from typing import List, Dict, Any
import yaml, os
ALL_TYPES=["RE","SU","AS","TOD","REN","IOU","IOD","UCL","UCS","TO","REE","TS","BP","ST","CNE","RR","UUS","EGL","COL","RDS","BE","AIB","CS","RTS","EF"]
def load_weights(path: str) -> Dict[str, Dict[str, Dict[str, int]]]:
    if not os.path.exists(path): return {}
    with open(path,"r",encoding="utf-8") as f: return yaml.safe_load(f) or {}
def aggregate(detector_results: List[Dict[str, Any]], weights_yaml: str) -> Dict[str, float]:
    weights=load_weights(weights_yaml); scores={t:0.0 for t in ALL_TYPES}
    for res in detector_results:
        tool=res.get("tool"); found_map=res.get("found",{}); wtool=weights.get(tool,{})
        for t in ALL_TYPES:
            present=found_map.get(t,-1)
            w = wtool.get(t,{}).get("reported",0) if present==1 else (wtool.get(t,{}).get("not_reported",0) if present==0 else 0)
            scores[t]+=w
    return scores
