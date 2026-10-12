import tempfile
import unittest
from pathlib import Path

from automender.detectors.base import FakeDetector
from automender.detectors.ensemble import DetectorEnsemble
from automender.types import Finding
from automender.validation.compiler import SolidityCompiler, pragma_version
from automender.validation.quality import dtw_distance, evaluate_quality, levenshtein_distance, terminal_reward


class DetectionValidationTest(unittest.TestCase):
    def test_unavailable_is_neutral_but_success_negative_vote_counts(self):
        finding = Finding("A", "RE", "x.sol", function="f")
        weights = {"A": {"RE": {"reported": 2, "not_reported": -1}}, "B": {"RE": {"reported": 1, "not_reported": -1}}}
        ensemble = DetectorEnsemble([FakeDetector("A", [finding], ["RE"]), FakeDetector("B", [], ["RE"], "unavailable")], weights, strict=False)
        accepted, runs, scores = ensemble.detect("x.sol")
        self.assertEqual(len(accepted), 1)
        self.assertEqual(scores[finding.segment_key], 2)
        ensemble = DetectorEnsemble([FakeDetector("A", [finding]), FakeDetector("B", [], status="success")], weights, strict=False)
        _, _, scores = ensemble.detect("x.sol")
        self.assertEqual(scores[finding.segment_key], 1)

    def test_strict_profile_rejects_missing_tool(self):
        ensemble = DetectorEnsemble([FakeDetector("A", status="unavailable")], {}, strict=True)
        with self.assertRaises(RuntimeError): ensemble.detect("x.sol")

    def test_dtw_levenshtein_gas_quality_reward(self):
        self.assertEqual(dtw_distance(["a", "b"], ["a", "c"]), 1)
        self.assertEqual(levenshtein_distance(["a", "b"], ["a", "x", "b"]), 1)
        quality = evaluate_quality("contract A{}", "contract A { uint x; }", [], [], True, True, 100, 90)
        self.assertEqual(quality.gas_increase, 0)
        self.assertTrue(quality.valid)
        self.assertAlmostEqual(terminal_reward(quality), 1 / (1 + quality.total_cost))
        invalid = evaluate_quality("contract A{}", "contract A{}", [], [Finding("A", "RE", "x")], True, True)
        self.assertFalse(invalid.valid)
        self.assertEqual(invalid.total_cost, 10000)
        self.assertEqual(terminal_reward(invalid), -1)

    def test_compiler_missing_never_passes_and_pragma(self):
        self.assertEqual(pragma_version("pragma solidity ^0.8.20;"), "0.8.20")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "A.sol"; path.write_text("contract A{}")
            result = SolidityCompiler("definitely-no-solc-here").compile(str(path))
            self.assertFalse(result.ok)
            self.assertEqual(result.status, "unavailable")


if __name__ == "__main__":
    unittest.main()
