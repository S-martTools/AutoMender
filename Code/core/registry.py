# Code/core/registry.py
from typing import Callable

def get_patch_generator() -> Callable[[str], str]:
    try:
        from moe_lora.cmoe_lora import generate_patch
        return generate_patch
    except Exception as e:
        def _fallback_generate_patch(prompt: str, **kwargs) -> str:
            return (
                "// PATCH BEGIN (fallback)\n"
                f"// CMoE-LoRA load failed: {e}\n"
                "// Replace get_patch_generator() when your environment is ready.\n"
                "// PATCH END\n"
            )
        return _fallback_generate_patch
