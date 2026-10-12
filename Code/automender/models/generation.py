from __future__ import annotations

import re
from typing import Any, List, Sequence

from ..types import RepairCandidate


CONTRACT_TAG = re.compile(r"<repaired_contract>\s*(.*?)\s*</repaired_contract>", re.DOTALL | re.IGNORECASE)
RATIONALE_TAG = re.compile(r"<repair_rationale>\s*(.*?)\s*</repair_rationale>", re.DOTALL | re.IGNORECASE)
SOLIDITY_BLOCK = re.compile(r"```(?:solidity)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def parse_repair_output(output: str, iteration: int = 0) -> RepairCandidate:
    contract_match = CONTRACT_TAG.search(output)
    if contract_match:
        contract = contract_match.group(1).strip()
    else:
        blocks = SOLIDITY_BLOCK.findall(output)
        contract = max(blocks, key=len).strip() if blocks else ""
    rationale_match = RATIONALE_TAG.search(output)
    rationale = rationale_match.group(1).strip() if rationale_match else ""
    complete = bool(contract and ("contract " in contract or "library " in contract or "interface " in contract) and "{" in contract and "}" in contract)
    return RepairCandidate(contract=contract, rationale=rationale, raw_output=output, iteration=iteration, parse_ok=complete)


class HuggingFaceGenerator:
    def __init__(self, model: Any, tokenizer: Any, max_new_tokens: int = 3072, communication_enabled: bool = True):
        self.model, self.tokenizer, self.max_new_tokens, self.communication_enabled = model, tokenizer, max_new_tokens, communication_enabled

    def generate(self, prompt: str, expert_labels: Sequence[str], candidates: int = 1, do_sample: bool = False) -> List[str]:
        import torch
        encoded = self.tokenizer(prompt, return_tensors="pt")
        device = next(self.model.parameters()).device
        encoded = {key: value.to(device) for key, value in encoded.items()}
        if hasattr(self.model, "set_route"):
            self.model.set_route(expert_labels)
        with torch.no_grad():
            outputs = self.model.generate(
                **encoded, expert_labels=expert_labels, communication=self.communication_enabled, max_new_tokens=self.max_new_tokens, do_sample=do_sample,
                num_return_sequences=candidates, pad_token_id=self.tokenizer.eos_token_id,
            )
        prompt_length = encoded["input_ids"].shape[1]
        return [self.tokenizer.decode(row[prompt_length:], skip_special_tokens=True) for row in outputs]
