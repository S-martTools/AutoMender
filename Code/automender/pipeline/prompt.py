from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..taxonomy import BUG_TO_EXPERT, EXPERT_DESCRIPTIONS
from ..types import Finding


def build_repair_prompt(contract: str, findings: Sequence[Finding], context: Sequence[Mapping[str, Any]] = (), iteration: int = 1, validation_feedback: str = "", cot: bool = True) -> str:
    details = "\n".join("- %s at %s:%s-%s (%s)" % (f.bug_type, f.path, f.line_start, f.line_end, f.evidence) for f in findings) or "- No localized findings supplied"
    categories = list(dict.fromkeys(BUG_TO_EXPERT[f.bug_type] for f in findings))
    recommendations = "\n".join("- %s: %s" % (category, EXPERT_DESCRIPTIONS[category]) for category in categories)
    retrieved = "\n\n".join(str(item.get("content", ""))[:2000] for item in context)
    reasoning = """Identifying — inspect every finding and its location.
Analyzing — trace the root cause, state, inheritance, and call dependencies.
Fixing — make the minimal complete-contract repair.
Rethinking — verify every finding and behavioral constraint.""" if cot else "Produce a minimal complete-contract repair for the supplied findings."
    return f"""You are repairing a Solidity contract. Iteration {iteration}.

Detected findings:
{details}

Analyzing — category guidance:
{recommendations}

Retrieved repair and semantic context:
{retrieved}

Previous validation feedback:
{validation_feedback or 'None'}

Reasoning protocol:
{reasoning}

Return the COMPLETE repaired contract, never a fragment and never text appended to the original.

Required output format:
<repaired_contract>
pragma solidity ...;
...complete source...
</repaired_contract>
<repair_rationale>Explain each modification and why behavior is preserved.</repair_rationale>

Original/current contract:
{contract}
"""
