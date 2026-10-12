from __future__ import annotations

from typing import Dict, Iterable, List, Set


EXPERT_CATEGORIES = (
    "reentrancy",
    "arithmetic",
    "unchecked_calls",
    "optimized_operations",
    "access_control",
    "transaction_dependence",
    "block_dependence",
)

BUG_NAMES: Dict[str, str] = {
    "RE": "reentrancy-eth",
    "SU": "suicidal",
    "AS": "arbitrary-send",
    "TOD": "tod",
    "REN": "reentrancy-no-eth",
    "IO": "integer-overflow",
    "UCL": "unchecked-lowlevel",
    "UCS": "unchecked-send",
    "TO": "tx-origin",
    "REE": "reentrancy-events",
    "TS": "timestamp",
    "BP": "block-other-parameters",
    "ST": "send-transfer",
    "CNE": "code-no-effects",
    "RR": "revert-require",
    "UUS": "unused-state",
    "EGL": "extra-gas-inloops",
    "RDS": "redundant-statements",
    "BE": "boolean-equal",
    "AIB": "array-instead-bytes",
    "CS": "constable-states",
    "RTS": "return-struct",
    "EF": "external-function",
    "COL": "costly-operations-loop",
}

BUG_TO_EXPERT: Dict[str, str] = {
    "RE": "reentrancy",
    "REN": "reentrancy",
    "REE": "reentrancy",
    "IO": "arithmetic",
    "UCL": "unchecked_calls",
    "UCS": "unchecked_calls",
    "ST": "optimized_operations",
    "CNE": "optimized_operations",
    "RR": "optimized_operations",
    "UUS": "optimized_operations",
    "EGL": "optimized_operations",
    "RDS": "optimized_operations",
    "BE": "optimized_operations",
    "AIB": "optimized_operations",
    "CS": "optimized_operations",
    "RTS": "optimized_operations",
    "EF": "optimized_operations",
    "COL": "optimized_operations",
    "SU": "access_control",
    "AS": "access_control",
    "TO": "access_control",
    "TOD": "transaction_dependence",
    "TS": "block_dependence",
    "BP": "block_dependence",
}

EXPERT_DESCRIPTIONS: Dict[str, str] = {
    "reentrancy": "Apply checks-effects-interactions and protect external calls.",
    "arithmetic": "Validate arithmetic results or use a checked arithmetic library.",
    "unchecked_calls": "Check call results and roll back or handle failures.",
    "optimized_operations": "Make semantics-preserving Solidity and gas optimizations.",
    "access_control": "Protect sensitive actions with correct authorization.",
    "transaction_dependence": "Prevent transaction-order-dependent state transitions.",
    "block_dependence": "Avoid miner-controlled block values; use a verifiable oracle.",
}

SEVERITY: Dict[str, str] = {
    **{key: "High" for key in ("RE", "SU", "AS", "TOD")},
    **{key: "Medium" for key in ("REN", "IO", "UCL", "UCS", "TO")},
    **{key: "Low" for key in ("REE", "TS", "BP")},
    **{key: "Opt" for key in ("ST", "CNE", "RR", "UUS", "EGL", "RDS", "BE", "AIB", "CS", "RTS", "EF", "COL")},
}


def normalize_bug_type(value: str) -> str:
    text = value.strip()
    upper = text.upper().replace("-", "_")
    if upper in BUG_NAMES:
        return upper
    lowered = text.lower().replace("_", "-")
    aliases = {name.lower(): bug for bug, name in BUG_NAMES.items()}
    aliases.update({"integer-underflow": "IO", "arithmetic": "IO"})
    if lowered not in aliases:
        raise ValueError(f"Unsupported bug type: {value}")
    return aliases[lowered]


def experts_for_bug_types(bug_types: Iterable[str]) -> List[str]:
    labels: Set[str] = set()
    for bug in bug_types:
        normalized = normalize_bug_type(bug)
        labels.add(BUG_TO_EXPERT[normalized])
    return [category for category in EXPERT_CATEGORIES if category in labels]
