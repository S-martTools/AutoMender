from dataclasses import dataclass
@dataclass
class RewardInputs:
    bug_removed: float; no_new_bugs: float; compile_ok: float; symexec_ok: float; gas_struct_score: float
@dataclass
class RewardWeights:
    w_bug_removed: float=0.5; w_no_new_bugs: float=0.2; w_compile_ok: float=0.1; w_symexec_ok: float=0.1; w_gas_struct: float=0.1
def compute_reward(inp: RewardInputs, w: RewardWeights) -> float:
    return (w.w_bug_removed*inp.bug_removed + w.w_no_new_bugs*inp.no_new_bugs +
            w.w_compile_ok*inp.compile_ok + w.w_symexec_ok*inp.symexec_ok + w.w_gas_struct*inp.gas_struct_score)
