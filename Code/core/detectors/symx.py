from .base import Detector, DetectorResult
class RSymXDetector(Detector):
    name="RSymX"
    def run(self, contract_path: str) -> DetectorResult:
        return DetectorResult(tool=self.name, found={}, raw="stub: integrate RSymX here")
