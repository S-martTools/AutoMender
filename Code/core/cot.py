from typing import List
COT_STEPS=[
 "Identify vulnerable patterns and exact lines.",
 "Analyze root cause and impacted state/flows.",
 "Propose a minimal code change (safe by default).",
 "Review for side effects, gas, and reentrancy.",
]
def plan(bug_types: List[str]) -> str:
    steps="\n".join(f"{i+1}. {s}" for i,s in enumerate(COT_STEPS))
    return f"CoT plan for {', '.join(bug_types) or 'unknown bugs'}:\n{steps}\n"
def extract_patch(generated_text: str) -> str:
    start=generated_text.find("// PATCH BEGIN"); end=generated_text.find("// PATCH END")
    return generated_text[start:end+len("// PATCH END")] if (start!=-1 and end!=-1 and end>start) else generated_text
