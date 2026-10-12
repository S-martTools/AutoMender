import csv
import json
import tempfile
import unittest
from pathlib import Path

from automender.data.labeling import label_pairs
from automender.data.audit import audit_pair_duplicates, audit_pairs_against_tests
from automender.data.solidity import normalize_tokens, solidity_tokens
from automender.taxonomy import BUG_NAMES, EXPERT_CATEGORIES, experts_for_bug_types


class TaxonomyAndDataTest(unittest.TestCase):
    def test_all_24_bug_types_map_to_seven_experts(self):
        self.assertEqual(len(BUG_NAMES), 24)
        labels = experts_for_bug_types(BUG_NAMES)
        self.assertEqual(set(labels), set(EXPERT_CATEGORIES))

    def test_comments_do_not_change_normalized_tokens(self):
        self.assertEqual(normalize_tokens("contract A{/*x*/uint x;}"), normalize_tokens("contract A{uint x;}"))

    def test_explicit_manifest_overrides_and_low_confidence_is_communication_only(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "pairs.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["vulnerable", "fixed"])
                writer.writeheader()
                writer.writerow({"vulnerable": "contract A { function f() public {} }", "fixed": "contract A { function f() public onlyOwner {} }"})
                writer.writerow({"vulnerable": "contract B {}", "fixed": "contract B { uint x; }"})
            first_report = label_pairs(str(csv_path), str(Path(directory) / "first"))
            rows = [json.loads(line) for line in (Path(directory) / "first" / "repair_samples.jsonl").read_text().splitlines()]
            manifest = Path(directory) / "labels.jsonl"
            manifest.write_text(json.dumps({"sample_id": rows[0]["sample_id"], "expert_labels": ["access_control"]}) + "\n")
            report = label_pairs(str(csv_path), str(Path(directory) / "second"), str(manifest))
            final = [json.loads(line) for line in (Path(directory) / "second" / "repair_samples.jsonl").read_text().splitlines()]
            self.assertEqual(final[0]["expert_labels"], ["access_control"])
            self.assertEqual(final[1]["expert_labels"], [])
            self.assertGreaterEqual(report["communication_only"], 1)

    def test_pair_internal_reuse_is_logged_but_whole_test_overlap_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "pairs.csv"
            contract = "contract A { uint x; }"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["vulnerable", "fixed"]); writer.writeheader()
                writer.writerow({"vulnerable": contract, "fixed": "contract A { uint y; }"})
                writer.writerow({"vulnerable": contract, "fixed": "contract A { uint y; }"})
            test_dir = Path(directory) / "test"; test_dir.mkdir(); (test_dir / "A.sol").write_text(contract)
            internal = audit_pair_duplicates(str(csv_path))
            self.assertTrue(internal["passed"])
            self.assertEqual(internal["duplicate_pairs"], 1)
            contamination = audit_pairs_against_tests(str(csv_path), {"test": str(test_dir)})
            self.assertFalse(contamination["passed"])


if __name__ == "__main__":
    unittest.main()
