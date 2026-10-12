from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from ..types import ContractSemantics
from .solidity import strip_comments


CONTRACT_RE = re.compile(r"\b(?:abstract\s+)?(?:contract|interface|library)\s+(\w+)(?:\s+is\s+([^\{]+))?\s*\{")
FUNCTION_RE = re.compile(r"\bfunction\s+(\w+|fallback|receive)?\s*\([^)]*\)")
MODIFIER_RE = re.compile(r"\bmodifier\s+(\w+)\s*\(")
CALL_RE = re.compile(r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+)\s*\(")
STATE_RE = re.compile(
    r"^\s*(?:mapping\s*\([^;]+\)|(?:u?int\d*|address|bool|bytes\d*|string|[A-Z]\w*)(?:\[\])*)"
    r"\s+(?:(?:public|private|internal|constant|immutable)\s+)*(\w+)\s*(?:=|;)", re.MULTILINE,
)
DANGEROUS = ("delegatecall", "selfdestruct", "tx.origin", "block.timestamp", "blockhash", ".call(", ".send(", ".transfer(", "assembly")


def extract_semantics(text: str, path: str = "") -> ContractSemantics:
    clean = strip_comments(text)
    contracts: List[str] = []
    inheritance: Dict[str, List[str]] = {}
    for match in CONTRACT_RE.finditer(clean):
        name = match.group(1)
        contracts.append(name)
        inheritance[name] = [part.strip() for part in (match.group(2) or "").split(",") if part.strip()]
    functions = [value or "fallback" for value in FUNCTION_RE.findall(clean)]
    calls = sorted(set(CALL_RE.findall(clean)))
    dangerous = sorted(operation for operation in DANGEROUS if operation in clean)
    return ContractSemantics(
        path=path, contracts=contracts, inheritance=inheritance,
        state_variables=STATE_RE.findall(clean), functions=functions,
        modifiers=MODIFIER_RE.findall(clean), calls=calls,
        dangerous_operations=dangerous,
    )


def extract_file(path: Path) -> ContractSemantics:
    return extract_semantics(path.read_text(encoding="utf-8", errors="replace"), str(path))
