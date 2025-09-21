from dataclasses import dataclass
from typing import Any, Dict, Callable, List
@dataclass
class PPOConfig: kl_coef: float=0.05; lr: float=5e-6; steps_per_update: int=8
class PPOTrainer:
    def __init__(self, patch_generator: Callable[[str], str], reward_fn: Callable[[Dict[str, Any]], float], cfg: PPOConfig=PPOConfig()):
        self.gen=patch_generator; self.reward_fn=reward_fn; self.cfg=cfg; self._buffer: List[Dict[str, Any]]=[]
    def step(self, prompt: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        patch=self.gen(prompt); traj={"prompt":prompt,"patch":patch,"meta":meta}; self._buffer.append(traj); return traj
    def update(self) -> Dict[str, Any]:
        if not self._buffer: return {"avg_reward":0.0,"n":0}
        rs=[self.reward_fn(t) for t in self._buffer]; avg=sum(rs)/len(rs); self._buffer.clear(); return {"avg_reward":avg,"n":len(rs)}
