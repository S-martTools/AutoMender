from .base import Detector, DetectorResult
class ILFDetector(Detector):
    name="ILF"
    def run(self, contract_path: str) -> DetectorResult:
        return DetectorResult(tool=self.name, found={}, raw="stub: integrate ILF here")
