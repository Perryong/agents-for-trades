"""Standardized agent output protocol — the contract between agents and the risk judge.

All agents must output an AgentSignal. The risk judge produces a TradeRecommendation
containing a TradeSpec (or None for no-trade decisions). These schemas are validated
at the LLM client boundary — malformed output raises AgentProtocolError.

This module is the single source of truth for agent output shape. Import from here,
not from api/schemas.py.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Agent output schema
# ---------------------------------------------------------------------------


class AgentSignal(BaseModel):
    """Structured output from a single analyst agent.

    Every agent (fundamentals, news, market, social, options flow, etc.)
    must produce this exact shape. The LLM client layer validates responses
    against this schema before they enter the pipeline.
    """

    signal_direction: Literal["bullish", "bearish", "neutral"]
    confidence: float = Field(ge=0, le=100)
    time_horizon: Literal["intraday", "swing", "position"]
    evidence: list[str] = Field(min_length=1)
    data_freshness: datetime
    valid_until: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "signal_direction": "bullish",
                    "confidence": 85.0,
                    "time_horizon": "swing",
                    "evidence": [
                        "Strong earnings beat — EPS $7.82 vs $7.10 est",
                        "Revenue up 22% YoY",
                    ],
                    "data_freshness": "2026-04-15T07:30:00",
                    "valid_until": "2026-04-15T09:30:00",
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# Trade specification
# ---------------------------------------------------------------------------


class TradeSpec(BaseModel):
    """Complete, executable trade specification.

    Contains everything needed to submit a paper or live trade — no
    human interpretation required. For options trades, strike/expiry/
    contract_type are mandatory.
    """

    ticker: str = Field(min_length=1)
    direction: Literal["BUY", "SELL"]
    trade_type: Literal["equity", "option"]
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    profit_target: float = Field(gt=0)
    position_size: int = Field(gt=0)
    strike: float | None = None
    expiry: str | None = None  # YYYY-MM-DD
    contract_type: Literal["call", "put"] | None = None

    @model_validator(mode="after")
    def validate_options_fields(self):
        if self.trade_type == "option":
            missing = []
            if self.strike is None:
                missing.append("strike")
            if self.expiry is None:
                missing.append("expiry")
            if self.contract_type is None:
                missing.append("contract_type")
            if missing:
                raise ValueError(
                    f"{', '.join(missing)} required for option trade_type"
                )
        return self

    @model_validator(mode="after")
    def validate_stop_loss_direction(self):
        if self.direction == "BUY" and self.stop_loss >= self.entry_price:
            raise ValueError(
                f"stop_loss ({self.stop_loss}) must be below entry_price "
                f"({self.entry_price}) for BUY direction"
            )
        if self.direction == "SELL" and self.stop_loss <= self.entry_price:
            raise ValueError(
                f"stop_loss ({self.stop_loss}) must be above entry_price "
                f"({self.entry_price}) for SELL direction"
            )
        return self


# ---------------------------------------------------------------------------
# Trade outcome taxonomy
# ---------------------------------------------------------------------------


class TradeOutcome(str, Enum):
    """Closed-set exit scenario for a trade.

    Used for meaningful performance analysis — distinguishes between
    different types of wins and losses.
    """

    STOP_LOSS_HIT = "STOP_LOSS_HIT"
    PROFIT_TARGET_HIT = "PROFIT_TARGET_HIT"
    EARLY_CLOSE = "EARLY_CLOSE"
    EXPIRED_WORTHLESS = "EXPIRED_WORTHLESS"
    PARTIAL_FILL = "PARTIAL_FILL"
    ASSIGNMENT = "ASSIGNMENT"


# ---------------------------------------------------------------------------
# Agent signal summary (for reasoning chain)
# ---------------------------------------------------------------------------


class AgentSignalSummary(BaseModel):
    """Per-agent summary within a TradeRecommendation's reasoning chain.

    Shows each agent's contribution to the final decision, including
    whether they dissented from the majority.
    """

    agent_name: str
    signal_direction: Literal["bullish", "bearish", "neutral"]
    confidence: float = Field(ge=0, le=100)
    evidence: list[str]
    is_dissenting: bool = False


# ---------------------------------------------------------------------------
# Trade recommendation
# ---------------------------------------------------------------------------


class TradeRecommendation(BaseModel):
    """Complete recommendation from the risk judge.

    Contains either a TradeSpec (actionable trade) or a no-trade decision
    with documented reasoning. The reasoning_chain shows how each agent's
    signal contributed to the final decision.
    """

    trade_spec: TradeSpec | None
    approval_status: Literal[
        "pending_review", "approved", "rejected", "modified", "auto_approved"
    ]
    reasoning_chain: list[AgentSignalSummary]
    no_trade_reason: str | None = None
    confidence: float = Field(ge=0, le=100)
    valid_until: datetime
    ticker: str

    @model_validator(mode="after")
    def validate_no_trade_has_reason(self):
        if self.trade_spec is None and not self.no_trade_reason:
            raise ValueError(
                "no_trade_reason is required when trade_spec is None"
            )
        return self
