"""Exposure coach service.

Synthesizes breadth + regime + top/bottom signals into a capital allocation
decision: how much to commit to equities right now.

Outputs: exposure ceiling (0-100%), posture (NEW_ENTRY_ALLOWED | REDUCE_ONLY | CASH_PRIORITY).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from .regime_detector import detect_regime, RegimeClassification
from .market_signals import detect_market_top, detect_ftd, TopSignal, BottomSignal


PostureType = Literal["NEW_ENTRY_ALLOWED", "REDUCE_ONLY", "CASH_PRIORITY"]


@dataclass
class ExposureDecision:
    """Capital allocation decision."""
    exposure_ceiling: float      # 0-100%
    posture: PostureType
    growth_vs_value_bias: str    # "growth" | "value" | "neutral"
    regime: str                  # From regime detector
    breadth_label: str           # From breadth scorer
    top_probability: float       # From top detector
    ftd_state: str               # From FTD detector
    rationale: str
    computed_at: datetime


def compute_exposure() -> ExposureDecision:
    """Synthesize all signals into an exposure decision."""
    now = datetime.now(timezone.utc)

    # Gather signals (all best-effort — partial inputs OK)
    try:
        regime_result = detect_regime()
    except Exception:
        regime_result = None

    try:
        top_signal = detect_market_top()
    except Exception:
        top_signal = TopSignal(0, 0, 0, 0)

    try:
        bottom_signal = detect_ftd()
    except Exception:
        bottom_signal = BottomSignal(0, 0, False, 0, "no_correction")

    # Extract key values
    regime = regime_result.regime if regime_result else "Transitional"
    breadth = regime_result.breadth_score if regime_result else 50
    breadth_label = regime_result.breadth_label if regime_result else "Moderate"
    top_prob = top_signal.top_probability
    ftd_state = bottom_signal.state

    # Decision logic
    rationale_parts = []

    # Base exposure from regime
    regime_exposure = {
        "Broadening": 90,
        "Concentration": 60,
        "Transitional": 50,
        "Inflationary": 40,
        "Contraction": 20,
    }.get(regime, 50)
    rationale_parts.append(f"Regime ({regime}): base {regime_exposure}%")

    # Adjust for breadth
    if breadth >= 70:
        regime_exposure = min(100, regime_exposure + 10)
        rationale_parts.append(f"Breadth healthy ({breadth:.0f}): +10%")
    elif breadth < 40:
        regime_exposure = max(0, regime_exposure - 15)
        rationale_parts.append(f"Breadth weak ({breadth:.0f}): -15%")

    # Adjust for top signal
    if top_prob > 60:
        regime_exposure = max(0, regime_exposure - 20)
        rationale_parts.append(f"Top signal elevated ({top_prob:.0f}%): -20%")
    elif top_prob > 40:
        regime_exposure = max(0, regime_exposure - 10)
        rationale_parts.append(f"Top signal moderate ({top_prob:.0f}%): -10%")

    # Adjust for FTD (positive signal after correction)
    if ftd_state == "ftd_confirmed":
        regime_exposure = min(100, regime_exposure + 15)
        rationale_parts.append("FTD confirmed: +15%")
    elif ftd_state == "correcting":
        regime_exposure = max(0, regime_exposure - 10)
        rationale_parts.append("Correcting (no FTD): -10%")

    # Determine posture
    if regime_exposure >= 60:
        posture: PostureType = "NEW_ENTRY_ALLOWED"
    elif regime_exposure >= 30:
        posture = "REDUCE_ONLY"
    else:
        posture = "CASH_PRIORITY"

    # Growth vs value bias from regime
    if regime in ("Broadening", "Transitional"):
        bias = "growth"
    elif regime in ("Inflationary",):
        bias = "value"
    else:
        bias = "neutral"

    return ExposureDecision(
        exposure_ceiling=round(max(0, min(100, regime_exposure)), 1),
        posture=posture,
        growth_vs_value_bias=bias,
        regime=regime,
        breadth_label=breadth_label,
        top_probability=top_prob,
        ftd_state=ftd_state,
        rationale="; ".join(rationale_parts),
        computed_at=now,
    )
