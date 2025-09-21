from typing import List, Dict, Any
import regex as re
def tokenize(text: str) -> List[str]:
    return re.findall(r"\p{L}+\p{M}*|\p{N}+", text.lower())
def simple_retrieval(query: str, corpus: List[Dict[str, Any]], topk: int = 5) -> List[Dict[str, Any]]:
    qset = set(tokenize(query)); scored=[]
    for doc in corpus:
        dset=set(tokenize(doc.get("text",""))); score=len(qset & dset)
        if score>0: scored.append((score,doc))
    scored.sort(key=lambda x:x[0], reverse=True)
    return [d for _,d in scored[:topk]]
def build_prompt(contract_text: str, bug_reports: List[Dict[str, Any]], knowledge: List[Dict[str, Any]]) -> str:
    s=[]; s.append("You are a smart-contract repair assistant. Produce a minimal, secure patch.")
    s.append("\n[CONTRACT]\n"+contract_text[:12000])
    if bug_reports: s.append("\n[DETECTED_BUGS]\n"+"\n".join(f"- {b.get('type','?')}: {b.get('detail','')}" for b in bug_reports))
    if knowledge:   s.append("\n[KNOWLEDGE]\n"+"\n".join(f"- {k.get('title','note')}: {k.get('snippet','')}" for k in knowledge[:10]))
    s.append("\n[TASK]\nFollow CoT: identify → analyze → patch → review. Return only the patched code block.")
    return "\n".join(s)
