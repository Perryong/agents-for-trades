"""Tests for tradingagents.agents.protocol — standardized agent output schemas."""

import pytest
from datetime import datetime, timedelta
from tradingagents.agents.protocol import (
    AgentSignal,
    TradeSpec,
    TradeRecommendation,
    TradeOutcome,
    AgentSignalSummary,
)
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# AgentSignal tests
# ---------------------------------------------------------------------------


class TestAgentSignal:
    """Tests for the AgentSignal Pydantic model."""

    def _valid_signal(self, **overrides):
        defaults = {
            "signal_direction": "bullish",
            "confidence": 85.0,
            "time_horizon": "swing",
            "evidence": ["Strong earnings beat", "Revenue up 22% YoY"],
            "data_freshness": datetime(2026, 4, 15, 7, 30),
            "valid_until": datetime(2026, 4, 15, 9, 30),
        }
        defaults.update(overrides)
        return AgentSignal(**defaults)

    def test_valid_construction(self):
        signal = self._valid_signal()
        assert signal.signal_direction == "bullish"
        assert signal.confidence == 85.0
        assert signal.time_horizon == "swing"
        assert len(signal.evidence) == 2

    def test_bearish_direction(self):
        signal = self._valid_signal(signal_direction="bearish")
        assert signal.signal_direction == "bearish"

    def test_neutral_direction(self):
        signal = self._valid_signal(signal_direction="neutral")
        assert signal.signal_direction == "neutral"

    def test_rejects_invalid_direction(self):
        with pytest.raises(ValidationError):
            self._valid_signal(signal_direction="maybe")

    def test_rejects_confidence_below_zero(self):
        with pytest.raises(ValidationError):
            self._valid_signal(confidence=-1.0)

    def test_rejects_confidence_above_100(self):
        with pytest.raises(ValidationError):
            self._valid_signal(confidence=101.0)

    def test_confidence_boundary_zero(self):
        signal = self._valid_signal(confidence=0.0)
        assert signal.confidence == 0.0

    def test_confidence_boundary_100(self):
        signal = self._valid_signal(confidence=100.0)
        assert signal.confidence == 100.0

    def test_rejects_empty_evidence(self):
        with pytest.raises(ValidationError):
            self._valid_signal(evidence=[])

    def test_rejects_invalid_time_horizon(self):
        with pytest.raises(ValidationError):
            self._valid_signal(time_horizon="weekly")

    def test_all_time_horizons(self):
        for horizon in ["intraday", "swing", "position"]:
            signal = self._valid_signal(time_horizon=horizon)
            assert signal.time_horizon == horizon

    def test_json_serialization(self):
        signal = self._valid_signal()
        data = signal.model_dump(mode="json")
        assert data["signal_direction"] == "bullish"
        assert data["confidence"] == 85.0
        assert isinstance(data["evidence"], list)


# ---------------------------------------------------------------------------
# TradeSpec tests
# ---------------------------------------------------------------------------


class TestTradeSpec:
    """Tests for the TradeSpec Pydantic model."""

    def _valid_equity_spec(self, **overrides):
        defaults = {
            "ticker": "AAPL",
            "direction": "BUY",
            "trade_type": "equity",
            "entry_price": 198.30,
            "stop_loss": 194.00,
            "profit_target": 208.00,
            "position_size": 50,
        }
        defaults.update(overrides)
        return TradeSpec(**defaults)

    def _valid_options_spec(self, **overrides):
        defaults = {
            "ticker": "NVDA",
            "direction": "BUY",
            "trade_type": "option",
            "entry_price": 3.50,
            "stop_loss": 2.10,
            "profit_target": 5.25,
            "position_size": 2,
            "strike": 142.50,
            "expiry": "2026-05-16",
            "contract_type": "call",
        }
        defaults.update(overrides)
        return TradeSpec(**defaults)

    def test_valid_equity_spec(self):
        spec = self._valid_equity_spec()
        assert spec.ticker == "AAPL"
        assert spec.direction == "BUY"
        assert spec.trade_type == "equity"
        assert spec.strike is None
        assert spec.expiry is None
        assert spec.contract_type is None

    def test_valid_options_spec(self):
        spec = self._valid_options_spec()
        assert spec.ticker == "NVDA"
        assert spec.trade_type == "option"
        assert spec.strike == 142.50
        assert spec.expiry == "2026-05-16"
        assert spec.contract_type == "call"

    def test_options_requires_strike(self):
        with pytest.raises(ValidationError, match="strike.*required"):
            self._valid_options_spec(strike=None)

    def test_options_requires_expiry(self):
        with pytest.raises(ValidationError, match="expiry.*required"):
            self._valid_options_spec(expiry=None)

    def test_options_requires_contract_type(self):
        with pytest.raises(ValidationError, match="contract_type.*required"):
            self._valid_options_spec(contract_type=None)

    def test_buy_stop_loss_must_be_below_entry(self):
        with pytest.raises(ValidationError, match="stop_loss.*below.*entry"):
            self._valid_equity_spec(
                direction="BUY", entry_price=100.0, stop_loss=105.0
            )

    def test_sell_stop_loss_must_be_above_entry(self):
        with pytest.raises(ValidationError, match="stop_loss.*above.*entry"):
            self._valid_equity_spec(
                direction="SELL", entry_price=100.0, stop_loss=95.0
            )

    def test_rejects_zero_entry_price(self):
        with pytest.raises(ValidationError):
            self._valid_equity_spec(entry_price=0)

    def test_rejects_zero_position_size(self):
        with pytest.raises(ValidationError):
            self._valid_equity_spec(position_size=0)

    def test_sell_direction(self):
        spec = self._valid_equity_spec(
            direction="SELL", entry_price=100.0, stop_loss=105.0, profit_target=90.0
        )
        assert spec.direction == "SELL"

    def test_put_contract_type(self):
        spec = self._valid_options_spec(contract_type="put")
        assert spec.contract_type == "put"

    def test_json_serialization(self):
        spec = self._valid_equity_spec()
        data = spec.model_dump(mode="json")
        assert data["ticker"] == "AAPL"
        assert data["entry_price"] == 198.30


# ---------------------------------------------------------------------------
# TradeOutcome tests
# ---------------------------------------------------------------------------


class TestTradeOutcome:
    """Tests for the TradeOutcome enum."""

    def test_all_values_exist(self):
        expected = {
            "STOP_LOSS_HIT",
            "PROFIT_TARGET_HIT",
            "EARLY_CLOSE",
            "EXPIRED_WORTHLESS",
            "PARTIAL_FILL",
            "ASSIGNMENT",
        }
        actual = {e.value for e in TradeOutcome}
        assert actual == expected

    def test_string_serialization(self):
        assert TradeOutcome.STOP_LOSS_HIT.value == "STOP_LOSS_HIT"
        assert TradeOutcome.PROFIT_TARGET_HIT.value == "PROFIT_TARGET_HIT"


# ---------------------------------------------------------------------------
# TradeRecommendation tests
# ---------------------------------------------------------------------------


class TestTradeRecommendation:
    """Tests for the TradeRecommendation model."""

    def _signal_summary(self, **overrides):
        defaults = {
            "agent_name": "fundamentals",
            "signal_direction": "bullish",
            "confidence": 91.0,
            "evidence": ["Strong earnings"],
            "is_dissenting": False,
        }
        defaults.update(overrides)
        return AgentSignalSummary(**defaults)

    def _valid_trade_rec(self, **overrides):
        defaults = {
            "trade_spec": TradeSpec(
                ticker="AAPL",
                direction="BUY",
                trade_type="equity",
                entry_price=198.30,
                stop_loss=194.00,
                profit_target=208.00,
                position_size=50,
            ),
            "approval_status": "pending_review",
            "reasoning_chain": [self._signal_summary()],
            "confidence": 87.0,
            "valid_until": datetime(2026, 4, 15, 9, 30),
            "ticker": "AAPL",
        }
        defaults.update(overrides)
        return TradeRecommendation(**defaults)

    def _valid_no_trade_rec(self, **overrides):
        defaults = {
            "trade_spec": None,
            "approval_status": "pending_review",
            "reasoning_chain": [self._signal_summary(confidence=35.0)],
            "no_trade_reason": "Confidence below threshold",
            "confidence": 35.0,
            "valid_until": datetime(2026, 4, 15, 9, 30),
            "ticker": "AAPL",
        }
        defaults.update(overrides)
        return TradeRecommendation(**defaults)

    def test_valid_trade_recommendation(self):
        rec = self._valid_trade_rec()
        assert rec.trade_spec is not None
        assert rec.confidence == 87.0
        assert rec.no_trade_reason is None

    def test_valid_no_trade_recommendation(self):
        rec = self._valid_no_trade_rec()
        assert rec.trade_spec is None
        assert rec.no_trade_reason == "Confidence below threshold"

    def test_no_trade_requires_reason(self):
        with pytest.raises(ValidationError, match="no_trade_reason.*required"):
            self._valid_no_trade_rec(no_trade_reason=None)

    def test_approval_statuses(self):
        for status in [
            "pending_review",
            "approved",
            "rejected",
            "modified",
            "auto_approved",
        ]:
            rec = self._valid_trade_rec(approval_status=status)
            assert rec.approval_status == status

    def test_rejects_invalid_approval_status(self):
        with pytest.raises(ValidationError):
            self._valid_trade_rec(approval_status="maybe")

    def test_dissenting_agent_in_chain(self):
        chain = [
            self._signal_summary(agent_name="fundamentals", is_dissenting=False),
            self._signal_summary(
                agent_name="options_flow",
                signal_direction="neutral",
                confidence=55.0,
                is_dissenting=True,
            ),
        ]
        rec = self._valid_trade_rec(reasoning_chain=chain)
        dissenting = [s for s in rec.reasoning_chain if s.is_dissenting]
        assert len(dissenting) == 1
        assert dissenting[0].agent_name == "options_flow"

    def test_json_serialization(self):
        rec = self._valid_trade_rec()
        data = rec.model_dump(mode="json")
        assert data["ticker"] == "AAPL"
        assert data["confidence"] == 87.0
        assert len(data["reasoning_chain"]) == 1


# ---------------------------------------------------------------------------
# AgentSignalSummary tests
# ---------------------------------------------------------------------------


class TestAgentSignalSummary:
    def test_valid_construction(self):
        summary = AgentSignalSummary(
            agent_name="news",
            signal_direction="bearish",
            confidence=72.0,
            evidence=["Negative sector news"],
            is_dissenting=True,
        )
        assert summary.agent_name == "news"
        assert summary.is_dissenting is True
