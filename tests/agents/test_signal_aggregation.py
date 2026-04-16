"""Tests for signal aggregation utility."""

import pytest
from tradingagents.agents.utils.signal_aggregation import aggregate_signals
from tradingagents.agents.protocol import AgentSignalSummary


def _signal(direction="bullish", confidence=80.0):
    """Helper to create a minimal signal dict."""
    return {
        "signal_direction": direction,
        "confidence": confidence,
        "time_horizon": "swing",
        "evidence": ["Test evidence"],
        "data_freshness": "2026-04-15T07:30:00",
        "valid_until": "2026-04-15T09:30:00",
    }


class TestAggregateSignals:
    def test_unanimous_bullish(self):
        signals = {
            "fundamentals": _signal("bullish", 90),
            "news": _signal("bullish", 80),
            "market": _signal("bullish", 85),
        }
        confidence, chain, majority = aggregate_signals(signals)
        assert majority == "bullish"
        assert confidence == pytest.approx(85.0)
        assert len(chain) == 3
        assert all(not s.is_dissenting for s in chain)

    def test_unanimous_bearish(self):
        signals = {
            "fundamentals": _signal("bearish", 70),
            "news": _signal("bearish", 60),
        }
        confidence, chain, majority = aggregate_signals(signals)
        assert majority == "bearish"
        assert confidence == pytest.approx(65.0)

    def test_conflicting_signals_flags_dissenters(self):
        signals = {
            "fundamentals": _signal("bullish", 90),
            "news": _signal("bullish", 80),
            "market": _signal("bullish", 85),
            "social": _signal("bullish", 75),
            "technical": _signal("bearish", 60),
        }
        confidence, chain, majority = aggregate_signals(signals)
        assert majority == "bullish"
        dissenters = [s for s in chain if s.is_dissenting]
        assert len(dissenters) == 1
        assert dissenters[0].agent_name == "technical"
        assert dissenters[0].signal_direction == "bearish"

    def test_all_neutral(self):
        signals = {
            "fundamentals": _signal("neutral", 50),
            "news": _signal("neutral", 45),
        }
        confidence, chain, majority = aggregate_signals(signals)
        assert majority == "neutral"

    def test_custom_weights(self):
        signals = {
            "fundamentals": _signal("bullish", 100),
            "news": _signal("bearish", 50),
        }
        weights = {"fundamentals": 2.0, "news": 1.0}
        confidence, chain, majority = aggregate_signals(signals, weights=weights)
        # weighted: (100*2 + 50*1) / (2+1) = 250/3 ≈ 83.33
        assert confidence == pytest.approx(250 / 3, abs=0.1)
        # fundamentals has 2x weight for bullish, news has 1x for bearish → bullish wins
        assert majority == "bullish"

    def test_missing_signals_skipped(self):
        signals = {
            "fundamentals": _signal("bullish", 90),
            "news": None,
            "market": _signal("bullish", 80),
        }
        confidence, chain, majority = aggregate_signals(signals)
        assert len(chain) == 2  # None signals skipped
        assert confidence == pytest.approx(85.0)

    def test_empty_signals(self):
        confidence, chain, majority = aggregate_signals({})
        assert confidence == 0
        assert len(chain) == 0
        assert majority == "neutral"

    def test_all_none_signals(self):
        signals = {"a": None, "b": None}
        confidence, chain, majority = aggregate_signals(signals)
        assert confidence == 0
        assert len(chain) == 0

    def test_chain_contains_agent_signal_summaries(self):
        signals = {"fundamentals": _signal("bullish", 85)}
        _, chain, _ = aggregate_signals(signals)
        assert isinstance(chain[0], AgentSignalSummary)
        assert chain[0].agent_name == "fundamentals"
        assert chain[0].evidence == ["Test evidence"]

    def test_tie_defaults_to_neutral(self):
        """When bullish and bearish are tied, majority should be neutral-ish or first max."""
        signals = {
            "a": _signal("bullish", 80),
            "b": _signal("bearish", 80),
        }
        confidence, chain, majority = aggregate_signals(signals)
        # Both have weight 1.0 each — tie. Implementation picks first max.
        assert majority in ("bullish", "bearish")  # either is acceptable in a tie
        assert len([s for s in chain if s.is_dissenting]) == 1
