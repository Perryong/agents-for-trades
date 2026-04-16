"""Tests for no-trade decision logic in risk manager."""

import pytest
from unittest.mock import MagicMock

from tradingagents.agents.managers.risk_manager import (
    _should_skip_trade,
    _build_no_trade_summary,
)


def _signal(direction="bullish", confidence=80.0):
    return {
        "signal_direction": direction,
        "confidence": confidence,
        "time_horizon": "swing",
        "evidence": ["Test"],
        "data_freshness": "2026-04-15T07:30:00",
        "valid_until": "2026-04-15T09:30:00",
    }


class TestShouldSkipTrade:
    def test_below_threshold_skips(self):
        signals = {"a": _signal("bullish", 40), "b": _signal("neutral", 30)}
        skip, reason = _should_skip_trade(signals, confidence_threshold=65.0)
        assert skip is True
        assert "below threshold" in reason.lower() or "confidence" in reason.lower()

    def test_above_threshold_does_not_skip(self):
        signals = {"a": _signal("bullish", 90), "b": _signal("bullish", 80)}
        skip, reason = _should_skip_trade(signals, confidence_threshold=65.0)
        assert skip is False
        assert reason is None

    def test_all_none_signals_skips(self):
        signals = {"a": None, "b": None}
        skip, reason = _should_skip_trade(signals, confidence_threshold=65.0)
        assert skip is True

    def test_heavily_conflicting_skips(self):
        """When signals are evenly split bullish/bearish, confidence is low."""
        signals = {
            "a": _signal("bullish", 80),
            "b": _signal("bearish", 80),
            "c": _signal("bearish", 75),
        }
        # Weighted avg confidence is (80+80+75)/3 ≈ 78.3 but direction is split
        # This test verifies the threshold check works on aggregated confidence
        skip, reason = _should_skip_trade(signals, confidence_threshold=90.0)
        assert skip is True

    def test_default_threshold(self):
        signals = {"a": _signal("bullish", 70)}
        skip, _ = _should_skip_trade(signals, confidence_threshold=70.0)
        assert skip is False  # exactly at threshold should not skip


class TestBuildNoTradeSummary:
    def test_summary_includes_ticker_and_reason(self):
        evaluations = [
            {"ticker": "AAPL", "reason": "Confidence below threshold (45%)"},
            {"ticker": "NVDA", "reason": "Conflicting signals"},
        ]
        summary = _build_no_trade_summary(evaluations)
        assert "AAPL" in summary
        assert "NVDA" in summary
        assert "Confidence below threshold" in summary

    def test_empty_evaluations(self):
        summary = _build_no_trade_summary([])
        assert "0" in summary or "no" in summary.lower()
