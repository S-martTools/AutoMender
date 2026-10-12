from __future__ import annotations

from typing import Tuple

import torch


def terminal_returns(reward: torch.Tensor, length: int, gamma: float = 1.0) -> torch.Tensor:
    powers = torch.arange(length - 1, -1, -1, device=reward.device, dtype=reward.dtype)
    return reward.unsqueeze(-1) * gamma ** powers


def ppo_loss(
    log_probs: torch.Tensor, old_log_probs: torch.Tensor, reference_log_probs: torch.Tensor,
    values: torch.Tensor, returns: torch.Tensor, entropy: torch.Tensor,
    mask: torch.Tensor, clip: float = 0.2, value_coefficient: float = 0.5,
    kl_coefficient: float = 0.01, entropy_coefficient: float = 0.01,
) -> Tuple[torch.Tensor, dict]:
    advantage = (returns - values).detach()
    ratio = torch.exp(log_probs - old_log_probs)
    unclipped = ratio * advantage
    clipped = torch.clamp(ratio, 1.0 - clip, 1.0 + clip) * advantage
    denominator = mask.sum().clamp_min(1.0)
    policy = -(torch.min(unclipped, clipped) * mask).sum() / denominator
    value = (((values - returns) ** 2) * mask).sum() / denominator
    reference_kl = (((log_probs - reference_log_probs) * mask).sum() / denominator)
    entropy_mean = (entropy * mask).sum() / denominator
    total = policy + value_coefficient * value + kl_coefficient * reference_kl - entropy_coefficient * entropy_mean
    return total, {
        "policy_loss": float(policy.detach().cpu()), "value_loss": float(value.detach().cpu()),
        "reference_kl": float(reference_kl.detach().cpu()), "entropy": float(entropy_mean.detach().cpu()),
    }
