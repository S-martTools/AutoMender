from .base import Detector, DetectorResult
import shutil, subprocess
class SecurifyDetector(Detector):
    name="Securify2.0"
    def run(self, contract_path: str) -> DetectorResult:
        if not shutil.which("securify"): return DetectorResult(tool=self.name, found={}, raw="securify not found")
        try:
            out=subprocess.check_output(["securify", contract_path], stderr=subprocess.STDOUT, text=True)
            return DetectorResult(tool=self.name, found={}, raw=out)
        except subprocess.CalledProcessError as e:
            return DetectorResult(tool=self.name, found={}, raw=str(e))
