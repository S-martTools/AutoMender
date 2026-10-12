from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Set

from ..data.solidity import solidity_tokens
from ..types import Finding, QualityBreakdown


def dtw_distance(left: Sequence[str], right: Sequence[str]) -> int:
    if not left:
        return len(right)
    previous = list(range(len(right) + 1))
    for i, token_left in enumerate(left, 1):
        current = [i] + [0] * len(right)
        for j, token_right in enumerate(right, 1):
            cost = 0 if token_left == token_right else 1
            current[j] = cost + min(previous[j], current[j - 1], previous[j - 1])
        previous = current
    return previous[-1]


def levenshtein_distance(left: Sequence[str], right: Sequence[str]) -> int:
    previous = list(range(len(right) + 1))
    for i, token_left in enumerate(left, 1):
        current = [i]
        for j, token_right in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (token_left != token_right)))
        previous = current
    return previous[-1]


def _keys(findings: Iterable[Finding]) -> Set[str]:
    return {finding.segment_key for finding in findings}


def evaluate_quality(
    original: str, repaired: str, before: Iterable[Finding], after: Iterable[Finding],
    compile_ok: bool, behavior_ok: bool, gas_before: Optional[int] = None, gas_after: Optional[int] = None,
    lambda_old: float = 1.0, lambda_new: float = 1.0, lambda_change: float = 0.5,
    invalid_penalty: float = 10000.0, distance: str = "dtw",
) -> QualityBreakdown:
    initial, final = _keys(before), _keys(after)
    residual = len(initial & final)
    new = len(final - initial)
    vulnerability_cost = lambda_old * residual + lambda_new * new
    gas_increase = float(max(0, (gas_after or 0) - (gas_before or 0))) if gas_before is not None and gas_after is not None else 0.0
    left, right = solidity_tokens(original), solidity_tokens(repaired)
    token_change = float((dtw_distance if distance == "dtw" else levenshtein_distance)(left, right))
    change_cost = gas_increase + lambda_change * token_change
    runtime_valid = compile_ok and behavior_ok
    valid = vulnerability_cost == 0 and runtime_valid
    return QualityBreakdown(
        residual_bugs=residual, new_bugs=new, vulnerability_cost=vulnerability_cost,
        compile_ok=compile_ok, behavior_ok=behavior_ok, runtime_valid=runtime_valid,
        gas_before=gas_before, gas_after=gas_after, gas_increase=gas_increase,
        token_change=token_change, change_cost=change_cost,
        valid=valid, total_cost=change_cost if valid else invalid_penalty,
    )


def terminal_reward(quality: QualityBreakdown) -> float:
    return 1.0 / (1.0 + quality.total_cost) if quality.valid else -1.0
