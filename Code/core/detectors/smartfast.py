from .base import Detector, DetectorResult
import re, pathlib
PATTERNS={"ST": r"\\bsend\\s*\\(", "AS": r"[+\\-*/]\\s*="}
class SmartFastDetector(Detector):
    name="SmartFast"
    def run(self, contract_path: str) -> DetectorResult:
        try: text=pathlib.Path(contract_path).read_text(encoding="utf-8", errors="ignore")
        except Exception as e: return DetectorResult(tool=self.name, found={}, raw=f"read error: {e}")
        found={}; 
        for k,pat in PATTERNS.items(): found[k]=1 if re.search(pat, text) else 0
        return DetectorResult(tool=self.name, found=found, raw="pattern-match")
