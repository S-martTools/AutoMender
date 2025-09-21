import subprocess, json, shutil
from .base import Detector, DetectorResult
class SlitherDetector(Detector):
    name="Slither"
    def run(self, contract_path: str) -> DetectorResult:
        if not shutil.which("slither"): return DetectorResult(tool=self.name, found={}, raw="slither not found")
        try:
            out=subprocess.check_output(["slither", contract_path, "--json", "-"], stderr=subprocess.STDOUT, text=True)
            found={}
            try:
                data=json.loads(out)
                for d in data.get("results",{}).get("detectors",[]):
                    check=d.get("check","").lower()
                    if "reentrancy" in check: found["RE"]=1
            except Exception: pass
            return DetectorResult(tool=self.name, found=found, raw=out)
        except subprocess.CalledProcessError as e:
            return DetectorResult(tool=self.name, found={}, raw=str(e))
