"""Eligibility gate for options strategy selection.

Provides a pure function `filter_strategies` that applies hard gates and soft
scoring to produce a shortlist of 3-6 strategies suitable for the LLM to
choose from.

Hard gates (eliminate candidates):
    1. Directional bias mismatch
    2. IV environment mismatch
    3. Multi-expiry required but unavailable
    4. Margin-intensive when margin unavailable or explicitly excluded

Soft scoring (rank survivors, don't eliminate):
    - Earnings proximity: +1 for earnings_signal=positive, -1 for negative
    - Theta environment: +1 if theta_env=positive (good for short-dated sells)

Returns top 6 candidates by score. If fewer than 3 pass hard gates, returns
all candidates rather than padding.
"""

from dataclasses import dataclass
from typing import Optional

from .models import StrategyRegistry


# ---------------------------------------------------------------------------
# Bias compatibility map
# ---------------------------------------------------------------------------

# Maps context bias -> set of registry bias values considered compatible.
# A strategy passes the bias gate if its bias list has overlap with the
# compatible set OR contains "any".
_BIAS_COMPAT: dict[str, set[str]] = {
    "bullish":          {"bullish", "bullish_volatile", "bullish_hedge", "any"},
    "bearish":          {"bearish", "bearish_volatile", "any"},
    "neutral":          {"neutral", "neutral_volatile", "neutral_quiet", "any"},
    "neutral_volatile": {"neutral", "neutral_volatile", "any"},
    "neutral_quiet":    {"neutral", "neutral_quiet", "any"},
    "bullish_volatile": {"bullish", "bullish_volatile", "any"},
    "bearish_volatile": {"bearish", "bearish_volatile", "any"},
    "bullish_hedge":    {"bullish", "bullish_hedge", "any"},
    "any":              {
        "bullish", "bearish", "neutral", "neutral_volatile", "neutral_quiet",
        "bullish_volatile", "bearish_volatile", "bullish_hedge", "any",
    },
}


# ---------------------------------------------------------------------------
# GateContext
# ---------------------------------------------------------------------------


@dataclass
class GateContext:
    """Input context for the eligibility gate."""

    bias: str
    iv_rank: float
    iv_env: str
    has_multi_expiry: bool
    available_margin: Optional[float]
    exclude_margin_intensive: bool
    min_oi_threshold: int
    near_dte: int
    iv_rank_for_earnings: float
    is_earnings_proximity: bool


# ---------------------------------------------------------------------------
# Gate function
# ---------------------------------------------------------------------------


def filter_strategies(registry: StrategyRegistry, context: GateContext) -> list[str]:
    """Return shortlist of 3-6 strategy names after hard gates + soft scoring.

    Args:
        registry: Loaded StrategyRegistry from registry.yaml.
        context:  Market context describing current conditions.

    Returns:
        Ordered list of strategy names (best first), 3-6 entries in normal
        conditions, or all passing candidates if fewer than 3 survive gates.
    """
    compatible_biases = _BIAS_COMPAT.get(context.bias, {context.bias, "any"})

    candidates: list[tuple[str, float]] = []

    for name, meta in registry.strategies.items():
        # ------------------------------------------------------------------
        # Hard gate 1: Directional bias
        # ------------------------------------------------------------------
        strategy_biases = set(meta.bias)
        if "any" not in strategy_biases:
            if not (strategy_biases & compatible_biases):
                continue

        # ------------------------------------------------------------------
        # Hard gate 2: IV environment
        # ------------------------------------------------------------------
        strategy_iv_envs = set(meta.iv_env)
        if "any" not in strategy_iv_envs:
            if context.iv_env != "any" and context.iv_env not in strategy_iv_envs:
                continue

        # ------------------------------------------------------------------
        # Hard gate 3: Multi-expiry requirement
        # ------------------------------------------------------------------
        if meta.requires_multi_expiry and not context.has_multi_expiry:
            continue

        # ------------------------------------------------------------------
        # Hard gate 4: Margin
        # ------------------------------------------------------------------
        if meta.margin_intensive:
            if context.available_margin is None or context.exclude_margin_intensive:
                continue

        # ------------------------------------------------------------------
        # Soft scoring
        # ------------------------------------------------------------------
        score: float = 0.0

        # Earnings proximity boost/penalty
        if context.is_earnings_proximity:
            if meta.earnings_signal == "positive":
                score += 1.0
            elif meta.earnings_signal == "negative":
                score -= 1.0

        # Theta environment — positive theta strategies get a small boost
        # when short-dated (near_dte <= 21 is a rough "short-dated" threshold)
        if meta.soft_score.theta_env == "positive" and context.near_dte <= 21:
            score += 0.5

        candidates.append((name, score))

    # Sort by score descending (stable — preserves YAML insertion order for ties)
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Return top 6; if fewer than 3 pass, return all
    shortlist = [name for name, _ in candidates[:6]]
    return shortlist
