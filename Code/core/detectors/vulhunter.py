from .base import Detector, DetectorResult
class VulHunterDetector(Detector):
    name="VulHunter"
    def run(self, contract_path: str) -> DetectorResult:
        return DetectorResult(tool=self.name, found={}, raw="stub: integrate your VulHunter here")
