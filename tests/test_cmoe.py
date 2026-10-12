import unittest

import torch
from torch import nn

from automender.models.cmoe_lora import CMoECausalLM, CMoELinear, inject_cmoe_lora
from automender.training.losses import conflict_regularization


class TinyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.proj = nn.Linear(2, 2, bias=False)

    def forward(self, value):
        return self.proj(value)


class CMoETest(unittest.TestCase):
    def make_model(self):
        base = TinyModel()
        inject_cmoe_lora(base, ["proj"], rank=1, alpha=1, dropout=0, lambda_comm=1)
        model = CMoECausalLM(base)
        for layer in model.cmoe_layers():
            for adapter in list(layer.experts.values()) + [layer.communication]:
                nn.init.ones_(adapter.A.weight); nn.init.ones_(adapter.B.weight)
        return model

    def test_hard_route_shared_adapter_and_inactive_gradient(self):
        model = self.make_model()
        value = torch.ones(1, 2)
        output = model(value, expert_labels=["reentrancy"]).sum()
        output.backward()
        layer = next(model.cmoe_layers())
        self.assertIsNotNone(layer.communication.A.weight.grad)
        self.assertIsNotNone(layer.experts["reentrancy"].A.weight.grad)
        self.assertIsNone(layer.experts["arithmetic"].A.weight.grad)

    def test_per_example_multilabel_route(self):
        model = self.make_model()
        output = model(torch.ones(2, 2), expert_labels=[["reentrancy"], ["reentrancy", "arithmetic"]])
        self.assertGreater(float(output[1].sum()), float(output[0].sum()))

    def test_conflict_hinge_and_second_order_backward(self):
        model = self.make_model()
        first = model.adapter_parameters("reentrancy")
        second = model.adapter_parameters("arithmetic")
        for parameter in first: parameter.data.fill_(1)
        for parameter in second: parameter.data.fill_(-1)
        repair_loss = sum((parameter ** 2).sum() for parameter in first + second)
        conflict, metrics = conflict_regularization(repair_loss, model, ["reentrancy", "arithmetic"])
        self.assertAlmostEqual(float(conflict.detach()), 1.0, places=5)
        self.assertEqual(metrics["conflict_rate"], 1.0)
        (repair_loss + 0.1 * conflict).backward()


if __name__ == "__main__":
    unittest.main()
