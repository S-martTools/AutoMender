class DetectorResult(dict): pass
class Detector:
    name="base"
    def run(self, contract_path: str) -> DetectorResult: raise NotImplementedError
