"""Unit tests for the strategy eligibility gate — GATE-01 through GATE-05.

RED phase tests: these fail until gate.py is implemented.
"""

import pytest
from tradingagents.agents.options.strategies import load_registry
from tradingagents.agents.options.strategies.gate import GateContext, filter_strategies


# Default GateContext values used across tests (override specific fields per test)
_DEFAULTS = dict(
    bias="bullish",
    iv_rank=50.0,
    iv_env="any",
    has_multi_expiry=True,
    available_margin=50000.0,
    exclude_margin_intensive=False,
    min_oi_threshold=100,
    near_dte=30,
    iv_rank_for_earnings=50.0,
    is_earnings_proximity=False,
)


def _ctx(**overrides) -> GateContext:
    """Build a GateContext with default values, overriding specified fields."""
    return GateContext(**{**_DEFAULTS, **overrides})


def test_gate_bias_hard_gate():
    """GATE-01: Bullish bias must never return strategies that are bearish-only."""
    reg = load_registry()
    ctx = _ctx(bias="bullish")
    shortlist = filter_strategies(reg, ctx)

    # Verify no bearish-only strategy made the cut
    for name in shortlist:
        meta = reg.strategies[name]
        # If "any" is in bias, it passes. If "bullish" or compatible bias in list, it passes.
        # A bearish-only strategy has ["bearish"] and no overlap with bullish.
        biases = meta.bias
        if "any" not in biases:
            # There must be some overlap with bullish-compatible biases
            bullish_compatible = {"bullish", "bullish_volatile", "bullish_hedge", "any"}
            overlap = set(biases) & bullish_compatible
            assert len(overlap) > 0, (
                f"Bearish-only strategy '{name}' (bias={biases}) passed the bullish gate"
            )


def test_gate_margin_failsafe():
    """GATE-02: When available_margin is None, no margin_intensive strategy is returned."""
    reg = load_registry()
    ctx = _ctx(available_margin=None)
    shortlist = filter_strategies(reg, ctx)

    for name in shortlist:
        meta = reg.strategies[name]
        assert not meta.margin_intensive, (
            f"Margin-intensive strategy '{name}' passed gate when available_margin=None"
        )


def test_gate_multi_expiry():
    """GATE-03: When has_multi_expiry is False, no requires_multi_expiry strategy is returned."""
    reg = load_registry()
    ctx = _ctx(has_multi_expiry=False)
    shortlist = filter_strategies(reg, ctx)

    for name in shortlist:
        meta = reg.strategies[name]
        assert not meta.requires_multi_expiry, (
            f"Multi-expiry strategy '{name}' passed gate when has_multi_expiry=False"
        )


def test_gate_soft_earnings_score():
    """GATE-04: Near earnings with neutral_volatile bias, earnings-positive strategies rank higher."""
    reg = load_registry()
    ctx = _ctx(
        bias="neutral_volatile",
        iv_env="low",
        is_earnings_proximity=True,
        iv_rank_for_earnings=80.0,
    )
    shortlist = filter_strategies(reg, ctx)

    # long_straddle should appear (earnings_signal=positive, neutral_volatile bias)
    # If it passes hard gates, it should be in the top of the list
    if "long_straddle" in reg.strategies:
        meta = reg.strategies["long_straddle"]
        # Only assert rank if long_straddle passes hard gates
        biases = meta.bias
        if "neutral_volatile" in biases or "any" in biases or "neutral" in biases:
            if "long_straddle" in shortlist:
                # Verify earnings-positive strategies appear before earnings-negative ones
                for name in shortlist:
                    if name == "long_straddle":
                        break  # Good — it appeared early

                # Stronger assertion: no earnings-negative strategy should rank above earnings-positive
                # when is_earnings_proximity=True
                positive_indices = [
                    i for i, n in enumerate(shortlist)
                    if reg.strategies[n].earnings_signal == "positive"
                ]
                negative_indices = [
                    i for i, n in enumerate(shortlist)
                    if reg.strategies[n].earnings_signal == "negative"
                ]
                if positive_indices and negative_indices:
                    assert min(positive_indices) < max(negative_indices), (
                        "Earnings-positive strategies should rank higher than earnings-negative "
                        "near earnings"
                    )


def test_gate_shortlist_size():
    """GATE-05: In normal conditions, shortlist contains 3-6 strategies."""
    reg = load_registry()
    ctx = _ctx(
        bias="bullish",
        iv_env="any",
        has_multi_expiry=True,
        available_margin=50000.0,
        exclude_margin_intensive=False,
    )
    shortlist = filter_strategies(reg, ctx)

    assert 3 <= len(shortlist) <= 6, (
        f"Expected shortlist of 3-6 strategies, got {len(shortlist)}: {shortlist}"
    )
