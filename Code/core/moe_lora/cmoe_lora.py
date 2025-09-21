# Code/moe_lora/cmoe_lora.py
import os, re, math
from typing import Dict, Any

# 可按需覆盖的通讯设置
os.environ.setdefault("NCCL_P2P_DISABLE", "1")
os.environ.setdefault("NCCL_IB_DISABLE", "1")

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForCausalLM

SYSTEM_PROMPT_ZH = "你是一名智能合约专家，精通Solidity语言，能够撰写和修复漏洞合约代码。"
SYSTEM_PROMPT_EN = "You are a Solidity smart-contract expert. You will be given a vulnerable contract and bug locations; return the fixed Solidity code."

# ---------- 基本模块：LoRA / CMoE ----------

class MOELoRALinear(nn.Module):
    def __init__(self, base_layer: nn.Linear, **kw):
        super().__init__()
        self.base = base_layer
        in_features, out_features = base_layer.in_features, base_layer.out_features
        self.moelora = MoELoRA(in_features, out_features, **kw)

    def forward(self, x):
        return self.base(x) + self.moelora(x)

def _replace_module_by_name(model: nn.Module, module_name: str, new_module: nn.Module):
    parts = module_name.split(".")
    sub = model
    for p in parts[:-1]:
        sub = getattr(sub, p) if not p.isdigit() else sub[int(p)]
    last = parts[-1]
    if last.isdigit():
        sub[int(last)] = new_module
    else:
        setattr(sub, last, new_module)

def apply_moelora_to_model(model: nn.Module, *, rank=8, alpha=32.0, dropout=0.1,
                           num_experts=3, top_k=1, dtype=torch.bfloat16,
                           target_modules=None):
    if target_modules is None:
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    for name, module in list(model.named_modules()):
        if isinstance(module, nn.Linear) and any(t in name for t in target_modules):
            _replace_module_by_name(
                model, name,
                MOELoRALinear(module, rank=rank, alpha=alpha, dropout=dropout,
                              num_experts=num_experts, top_k=top_k, dtype=dtype)
            )
        # 冻结基础权重
        if hasattr(module, "weight") and hasattr(module.weight, "requires_grad"):
            module.weight.requires_grad = False
        if getattr(module, "bias", None) is not None and hasattr(module.bias, "requires_grad"):
            module.bias.requires_grad = False
    return model

# ---------- 配置与单例 ----------
_TOKENIZER = None
_MODEL = None
_CFG: Dict[str, Any] = {}

def _load_cfg(path: str) -> Dict[str, Any]:
    import yaml
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def _init_once(cfg_path: str):
    global _TOKENIZER, _MODEL, _CFG
    if _MODEL is not None:
        return

    _CFG = _load_cfg(cfg_path)
    model_name = _CFG.get("model_name", "")
    if not model_name:
        raise RuntimeError("Please set Code/config/moe_lora.yaml:model_name to your base model path")

    device = _CFG.get("device", "cuda" if torch.cuda.is_available() else "cpu")
    dtype_str = str(_CFG.get("dtype", "bfloat16")).lower()
    dtype = torch.bfloat16 if "bf" in dtype_str else (torch.float16 if "16" in dtype_str else torch.float32)

    _TOKENIZER = AutoTokenizer.from_pretrained(model_name, use_fast=False, trust_remote_code=True)
    _MODEL = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, torch_dtype=dtype)

    _MODEL = apply_moelora_to_model(
        _MODEL,
        rank=int(_CFG.get("rank", 8)),
        alpha=float(_CFG.get("alpha", 32.0)),
        dropout=float(_CFG.get("dropout", 0.1)),
        num_experts=int(_CFG.get("num_experts", 3)),
        top_k=int(_CFG.get("top_k", 1)),
        dtype=dtype,
        target_modules=_CFG.get("target_modules", None),
    )

    # 可选：加载已训练的 MoE-LoRA 权重，仅包含新注入的参数
    weights_path = _CFG.get("weights_path", "")
    if weights_path and os.path.exists(weights_path):
        state = torch.load(weights_path, map_location="cpu")
        _MODEL.load_state_dict(state, strict=False)

    _MODEL.to(device).eval()
    _CFG["_device"] = device
    _CFG["_dtype"]  = str(dtype)

def _build_messages(contract_text: str, bug_desc: str, zh: bool = False) -> str:
    system = SYSTEM_PROMPT_ZH if zh else SYSTEM_PROMPT_EN
    user = (
        f"Vulnerable contract:\n{contract_text}\n\n"
        f"Bug locations/types:\n{bug_desc}\n"
        f"Return the fixed Solidity code only, wrapped between:\n"
        f"// PATCH BEGIN\n...code...\n// PATCH END"
    )
    # 若模型含 chat 模板则用之，否则退化为纯拼接
    try:
        return _TOKENIZER.apply_chat_template(
            [{"role": "system", "content": system},
             {"role": "user", "content": user}],
            tokenize=False,
            add_generation_prompt=True
        )
    except Exception:
        return f"<system>{system}</system>\n<user>{user}</user>\n<assistant>"

# ---------- 对外统一接口 ----------
@torch.inference_mode()
def generate_patch(prompt: str, *, experts: str = "", config_path: str = "Code/config/moe_lora.yaml", **kwargs) -> str:
    """
    Pipeline 统一调用接口：
      - prompt: 来自 RAG/CoT 的拼装提示词
      - experts: 逗号分隔的专家名（此演示实现未按专家名动态切换权重，但你可以在这里利用它）
      - config_path: CMoE-LoRA 配置文件路径
    """
    _init_once(config_path)
    device = _CFG.get("_device", "cpu")
    max_new_tokens = int(_CFG.get("max_new_tokens", 1024))
    zh = bool(_CFG.get("zh", False))

    # 尝试从 prompt 中抽取合约与漏洞提示；失败则直接使用 prompt
    c = re.search(r"\[CONTRACT\]\n(.*?)(?:\n\[|$)", prompt, flags=re.S)
    b = re.search(r"\[DETECTED_BUGS\]\n(.*?)(?:\n\[|$)", prompt, flags=re.S)
    if c:
        contract_text = c.group(1).strip()[:8000]
        bug_desc = (b.group(1).strip() if b else "Not specified")[:2000]
        text = _build_messages(contract_text, bug_desc, zh=zh)
    else:
        text = prompt

    inputs = _TOKENIZER([text], return_tensors="pt").to(device)
    gen_ids = _MODEL.generate(
        **inputs,
        do_sample=False,
        max_new_tokens=max_new_tokens,
        repetition_penalty=float(_CFG.get("repetition_penalty", 1.1)),
    )
    # 去掉提示词前缀，只保留新生成内容
    gen_only = [out[len(inp):] for inp, out in zip(inputs.input_ids, gen_ids)]
    decoded = _TOKENIZER.batch_decode(gen_only, skip_special_tokens=True)[0]

    # 兜底补丁标记，便于下游自动抽取
    if "// PATCH BEGIN" not in decoded:
        decoded = "// PATCH BEGIN\n/* TODO: insert patched Solidity code here */\n// PATCH END"
    return decoded