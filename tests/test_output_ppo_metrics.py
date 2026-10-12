import unittest

import torch

from automender.experiments.metrics import repair_metrics
from automender.experiments.matrix import experiment_matrix
from automender.models.generation import parse_repair_output
from automender.training.ppo import ppo_loss, terminal_returns


class OutputPPOTest(unittest.TestCase):
    def test_complete_contract_parser_does_not_append(self):
        output = "<repaired_contract>pragma solidity ^0.8.0; contract A {}</repaired_contract><repair_rationale>x</repair_rationale>"
        candidate = parse_repair_output(output)
        self.assertTrue(candidate.parse_ok)
        self.assertEqual(candidate.contract, "pragma solidity ^0.8.0; contract A {}")
        self.assertFalse(parse_repair_output("change line 2").parse_ok)

    def test_ppo_formula_runs(self):
        reward = torch.tensor([1.0])
        returns = terminal_returns(reward, 3, 1.0)
        self.assertTrue(torch.equal(returns, torch.ones(1, 3)))
        values = torch.zeros(1, 3, requires_grad=True)
        zeros = torch.zeros(1, 3, requires_grad=True)
        loss, details = ppo_loss(zeros, torch.zeros(1, 3), torch.zeros(1, 3), values, returns, torch.ones(1, 3), torch.ones(1, 3))
        loss.backward()
        self.assertIn("policy_loss", details)

    def test_metrics(self):
        value = repair_metrics(8, 1, 2)
        self.assertAlmostEqual(value["iou"], 8 / 11)
        self.assertAlmostEqual(value["precision"], 8 / 9)
        self.assertAlmostEqual(value["recall"], 0.8)

    def test_ablation_matrix_has_three_seeds_and_stable_ids(self):
        rows = experiment_matrix()
        self.assertEqual({row["seed"] for row in rows}, {42, 3407, 2025})
        self.assertEqual(len({row["run_id"] for row in rows}), len(rows))
        self.assertTrue(any(row["distance"] == "levenshtein" for row in rows))
        self.assertTrue(any(not row["communication"] and not row["conflict"] for row in rows))


if __name__ == "__main__":
    unittest.main()
