"""Pydantic v2 models for the strategy registry.

Provides type-safe loading and validation of registry.yaml entries.
Exported: StrategyMeta, LegDef, SoftScore, StrategyRegistry
"""

from typing import Literal, List
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

BiasType = Literal[
    "bullish",
    "bearish",
    "neutral",
    "neutral_volatile",
    "neutral_quiet",
    "bullish_volatile",
    "bearish_volatile",
    "bullish_hedge",
    "any",
]

IVEnvType = Literal["low", "high", "any"]

EarningsSignal = Literal["positive", "negative", "neutral"]

ThetaEnvScore = Literal["positive", "negative", "neutral"]

SideType = Literal["buy", "sell"]

OptionTypeStr = Literal["call", "put"]

ExpiryType = Literal["near", "far"]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SoftScore(BaseModel):
    """Soft scoring signals for ranking within eligible strategies."""

    theta_env: ThetaEnvScore = "neutral"
    skew: ThetaEnvScore = "neutral"


class StrategyMeta(BaseModel):
    """Metadata for a single strategy entry in the registry."""

    bias: List[BiasType]
    iv_env: List[IVEnvType]
    legs_count: int
    margin_intensive: bool
    requires_multi_expiry: bool
    earnings_signal: EarningsSignal = "neutral"
    default_width: float = 5.0
    soft_score: SoftScore = SoftScore()


class LegDef(BaseModel):
    """Definition for a single leg in an options strategy."""

    side: SideType
    type: OptionTypeStr
    quantity: int = 1
    strike_offset: int = 0
    expiry: ExpiryType = "near"


class StrategyRegistry(BaseModel):
    """Container for all strategies and their leg definitions."""

    strategies: dict[str, StrategyMeta]
    legs: dict[str, List[LegDef]]
