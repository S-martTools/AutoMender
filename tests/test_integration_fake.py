import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

import torch
import torch.nn.functional as F
from torch import nn

from automender.detectors.base import Detector
from automender.detectors.ensemble import DetectorEnsemble
from automender.pipeline.repair import IterativeRepairPipeline
from automender.models.cmoe_lora import CMoECausalLM, inject_cmoe_lora
from automender.training.losses import conflict_regularization
from automender.training.ppo import ppo_loss
from automender.types import DetectionRun, Finding
from automender.validation.behavior import BehaviorResult
from automender.validation.compiler import CompileResult


class ContentDetector(Detector):
    name = "Fake"
    supported_types = ("RE",)
    def run(self, contract_path):
        text = Path(contract_path).read_text()
        findings = [Finding(self.name, "RE", contract_path, function="withdraw")] if "BUG" in text else []
        return DetectionRun(self.name, "success", findings, paper_eligible=False)


class Generator:
    def generate(self, prompt, expert_labels, candidates=1):
        self.labels = expert_labels
        return ["<repaired_contract>pragma solidity ^0.8.0; contract Safe { function withdraw() public {} }</repaired_contract><repair_rationale>CEI applied.</repair_rationale>"]


class Compiler:
    def compile(self, path, version=""):
        return CompileResult("success", True, version or "0.8.0", 100)


class Behavior:
    def validate(self, original, repaired, manifest):
        return BehaviorResult("success", True, [{"oracle": "repair-invariant", "passed": True}])


class ToyCausalLM(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(11, 4)
        self.proj = nn.Linear(4, 4)
        self.lm_head = nn.Linear(4, 11)

    def forward(self, input_ids, labels=None, output_hidden_states=False, **kwargs):
        hidden = torch.tanh(self.proj(self.embedding(input_ids)))
        logits = self.lm_head(hidden)
        loss = F.cross_entropy(logits[:, :-1].reshape(-1, 11), labels[:, 1:].reshape(-1)) if labels is not None else None
        return SimpleNamespace(logits=logits, loss=loss, hidden_states=(hidden,))


class FakeIntegrationTest(unittest.TestCase):
    def test_toy_dapt_sft_and_ppo_updates(self):
        base = ToyCausalLM()
        for parameter in base.parameters(): parameter.requires_grad_(False)
        inject_cmoe_lora(base, ["proj"], rank=2, alpha=2, dropout=0)
        model = CMoECausalLM(base)
        tokens = torch.tensor([[1, 2, 3, 4]])
        # DAPT: shared communication adapter only.
        dapt_loss = model(input_ids=tokens, labels=tokens, expert_labels=[]).loss
        dapt_loss.backward()
        layer = next(model.cmoe_layers())
        self.assertIsNotNone(layer.communication.B.weight.grad)
        self.assertIsNone(layer.experts["reentrancy"].B.weight.grad)
        model.zero_grad()
        # Multi-label SFT: routed experts and differentiable conflict term.
        sft_loss = model(input_ids=tokens, labels=tokens, expert_labels=[["reentrancy", "arithmetic"]]).loss
        conflict, _ = conflict_regularization(sft_loss, model, [["reentrancy", "arithmetic"]])
        (sft_loss + 0.1 * conflict).backward()
        self.assertIsNotNone(layer.experts["reentrancy"].B.weight.grad)
        # PPO objective: old/reference policies are fixed tensors for this update.
        log_probs = torch.zeros(1, 3, requires_grad=True)
        values = torch.zeros(1, 3, requires_grad=True)
        ppo, _ = ppo_loss(log_probs, torch.zeros(1, 3), torch.zeros(1, 3), values, torch.ones(1, 3), torch.ones(1, 3), torch.ones(1, 3))
        ppo.backward()
        self.assertIsNotNone(values.grad)

    def test_three_stage_core_and_early_stopping(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(directory) / "A.sol"
            contract.write_text("pragma solidity ^0.8.0; contract A { function withdraw() public { /* BUG */ } }")
            manifest = Path(directory) / "cases.json"; manifest.write_text("{}")
            detector = ContentDetector()
            ensemble = DetectorEnsemble([detector], {"Fake": {"RE": {"reported": 1, "not_reported": -1}}}, strict=False)
            generator = Generator()
            pipeline = IterativeRepairPipeline(generator, ensemble, Compiler(), Behavior(), max_iterations=3)
            result = pipeline.repair(str(contract), str(manifest))
            self.assertTrue(result.success)
            self.assertEqual(result.iterations, 1)
            self.assertEqual(result.stop_reason, "valid_below_threshold")
            self.assertEqual(generator.labels, ["reentrancy"])
            self.assertNotIn("BUG", result.final_contract)
            self.assertFalse(result.paper_eligible)


if __name__ == "__main__":
    unittest.main()
