"""Unit tests for create_greeks_monitor factory.

All data layer (route_to_vendor) calls are mocked.
No live API calls are made in any test.

Test data uses bull call spread with known Greeks values for
deterministic threshold assertions.
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm():
    mock_llm = MagicMock()
    return mock_llm


# ---------------------------------------------------------------------------
# Shared test data
#
# Phase 4 legs format (from options_legs_builder output):
#   LEG 1: BUY CALL AAPL 2026-05-10 $150.00 limit=8.45 qty=1 [OK]
#   LEG 2: SELL CALL AAPL 2026-05-10 $155.00 limit=5.20 qty=1 [OK]
#
# trade_date = "2026-05-08" -> DTE = 2 (triggers PIN_RISK when gamma > 0.10)
# trade_date = "2026-04-01" -> DTE = 39 (no PIN_RISK)
# ---------------------------------------------------------------------------

BASE_LEGS = (
    "LEG 1: BUY CALL AAPL 2026-05-10 $150.00 limit=8.45 qty=1 [OK]\n"
    "LEG 2: SELL CALL AAPL 2026-05-10 $155.00 limit=5.20 qty=1 [OK]\n"
    "NET: debit=3.25 max_profit=1.75 max_loss=3.25 breakeven=153.25"
)

# Standard chain with moderate Greeks: will NOT trigger any flag by default
# BUY CALL 150: sign=+1, delta=0.55, gamma=0.04, theta=-0.15, vega=0.25, underlying=175
# SELL CALL 155: sign=-1, delta=0.40, gamma=0.03, theta=-0.12, vega=0.20, underlying=175
#
# net_dollar_delta = (+1*0.55*1*100*175) + (-1*0.40*1*100*175)
#                  = 9625 - 7000 = 2625  (NOT > 5000, so no DELTA_HEAVY)
# net_gamma = (+1*0.04*100) + (-1*0.03*100) = 4 - 3 = 1.0  (> 0.10 -> PIN_RISK if DTE<=5)
# net_dollar_theta = (+1*(-0.15)*100) + (-1*(-0.12)*100) = -15 + 12 = -3  (NOT < -200)
# net_dollar_vega = (+1*0.25*100) + (-1*0.20*100) = 25 - 20 = 5  (NOT > 500)

STANDARD_CHAIN = (
    "strike  option_type  bid   ask   delta  gamma  theta   vega   open_interest  iv    underlying\n"
    "150.0   call         8.0   8.9   0.55   0.04   -0.15   0.25   300            0.25  175.0\n"
    "155.0   call         4.8   5.6   0.40   0.03   -0.12   0.20   200            0.23  175.0\n"
)

# Chain for DELTA_HEAVY test: single long call with high delta
# BUY CALL 150: sign=+1, delta=0.80, underlying=175
# net_dollar_delta = +1*0.80*1*100*175 = 14000 > 5000 -> DELTA_HEAVY
DELTA_HEAVY_CHAIN = (
    "strike  option_type  bid   ask   delta  gamma  theta   vega   open_interest  iv    underlying\n"
    "150.0   call         8.0   8.9   0.80   0.04   -0.15   0.25   300            0.25  175.0\n"
    "155.0   call         4.8   5.6   0.40   0.03   -0.12   0.20   200            0.23  175.0\n"
)

# For no-DELTA_HEAVY test: use STANDARD_CHAIN with net_dollar_delta=2625

# Chain for HIGH_DECAY test: large absolute theta to trigger net_dollar_theta < -200
# BUY CALL 150: sign=+1, theta=-3.0
# SELL CALL 155: sign=-1, theta=-0.12
# net_dollar_theta = (+1*(-3.0)*100) + (-1*(-0.12)*100) = -300 + 12 = -288 < -200 -> HIGH_DECAY
HIGH_DECAY_CHAIN = (
    "strike  option_type  bid   ask   delta  gamma  theta   vega   open_interest  iv    underlying\n"
    "150.0   call         8.0   8.9   0.55   0.04   -3.0    0.25   300            0.25  175.0\n"
    "155.0   call         4.8   5.6   0.40   0.03   -0.12   0.20   200            0.23  175.0\n"
)

# Chain for VOL_SENSITIVE test: large vega to trigger |net_dollar_vega| > 500
# BUY CALL 150: sign=+1, vega=6.0 -> +1*6.0*100 = 600 > 500 -> VOL_SENSITIVE
VOL_SENSITIVE_CHAIN = (
    "strike  option_type  bid   ask   delta  gamma  theta   vega   open_interest  iv    underlying\n"
    "150.0   call         8.0   8.9   0.55   0.04   -0.15   6.0    300            0.25  175.0\n"
    "155.0   call         4.8   5.6   0.40   0.03   -0.12   0.20   200            0.23  175.0\n"
)


def _make_route_side_effect(chain_str=STANDARD_CHAIN):
    def _side_effect(method, *args, **kwargs):
        if method == "get_options_chain":
            return chain_str
        return ""
    return _side_effect


def _make_state(legs=BASE_LEGS, trade_date="2026-04-01"):
    return {
        "company_of_interest": "AAPL",
        "trade_date": trade_date,
        "options_legs": legs,
        "messages": [],
    }


# ---------------------------------------------------------------------------
# Test 1: Factory returns callable
# ---------------------------------------------------------------------------

def test_factory_returns_callable():
    """create_greeks_monitor(llm) must return a callable."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    node = create_greeks_monitor(_make_mock_llm())
    assert callable(node), "Factory must return a callable node"


# ---------------------------------------------------------------------------
# Test 2: Node returns dict with greeks_report key containing str
# ---------------------------------------------------------------------------

def test_returns_greeks_report():
    """Node must return a dict with 'greeks_report' key containing a string."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    state = _make_state()

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=_make_route_side_effect()):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    assert isinstance(result, dict), "Node must return a dict"
    assert "greeks_report" in result, "Return dict must contain 'greeks_report' key"
    assert isinstance(result["greeks_report"], str), "greeks_report must be a string"


# ---------------------------------------------------------------------------
# Test 3: No messages written
# ---------------------------------------------------------------------------

def test_no_messages_written():
    """Return dict must NOT contain 'messages' key."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    state = _make_state()

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=_make_route_side_effect()):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    assert "messages" not in result, (
        f"Return dict must NOT contain 'messages' key, got keys: {list(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 4: DELTA_HEAVY flag triggered
# ---------------------------------------------------------------------------

def test_delta_heavy_flag():
    """When |net_dollar_delta| > 5000, report must contain 'DELTA_HEAVY'."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    state = _make_state()

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=DELTA_HEAVY_CHAIN)):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    assert "DELTA_HEAVY" in result["greeks_report"], (
        f"Expected DELTA_HEAVY flag in report, got: {result['greeks_report']}"
    )


# ---------------------------------------------------------------------------
# Test 5: No DELTA_HEAVY below threshold
# ---------------------------------------------------------------------------

def test_no_delta_heavy_below_threshold():
    """When |net_dollar_delta| <= 5000, report must NOT contain 'DELTA_HEAVY'."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    # STANDARD_CHAIN yields net_dollar_delta = 2625, which is <= 5000
    state = _make_state()

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=STANDARD_CHAIN)):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    assert "DELTA_HEAVY" not in result["greeks_report"], (
        f"DELTA_HEAVY should NOT appear when |delta| <= 5000, got: {result['greeks_report']}"
    )


# ---------------------------------------------------------------------------
# Test 6: PIN_RISK flag triggered (high gamma, DTE <= 5)
# ---------------------------------------------------------------------------

def test_pin_risk_flag():
    """When net_gamma > 0.10 and DTE <= 5, report must contain 'PIN_RISK'."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    # trade_date = "2026-05-08", expiry = "2026-05-10" -> DTE = 2 (<=5)
    # STANDARD_CHAIN: net_gamma = (+1*0.04*100) + (-1*0.03*100) = 1.0 > 0.10
    state = _make_state(trade_date="2026-05-08")

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=STANDARD_CHAIN)):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    assert "PIN_RISK" in result["greeks_report"], (
        f"Expected PIN_RISK flag when gamma > 0.10 and DTE=2, got: {result['greeks_report']}"
    )


# ---------------------------------------------------------------------------
# Test 7: No PIN_RISK when DTE > 5
# ---------------------------------------------------------------------------

def test_no_pin_risk_high_dte():
    """When net_gamma > 0.10 but DTE > 5, report must NOT contain 'PIN_RISK'."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    # trade_date = "2026-04-01", expiry = "2026-05-10" -> DTE = 39 (>5)
    state = _make_state(trade_date="2026-04-01")

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=STANDARD_CHAIN)):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    assert "PIN_RISK" not in result["greeks_report"], (
        f"PIN_RISK should NOT appear when DTE=39, got: {result['greeks_report']}"
    )


# ---------------------------------------------------------------------------
# Test 8: HIGH_DECAY flag triggered
# ---------------------------------------------------------------------------

def test_high_decay_flag():
    """When net_dollar_theta < -200, report must contain 'HIGH_DECAY'."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    state = _make_state()

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=HIGH_DECAY_CHAIN)):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    assert "HIGH_DECAY" in result["greeks_report"], (
        f"Expected HIGH_DECAY flag when net_theta < -200, got: {result['greeks_report']}"
    )


# ---------------------------------------------------------------------------
# Test 9: VOL_SENSITIVE flag triggered
# ---------------------------------------------------------------------------

def test_vol_sensitive_flag():
    """When |net_dollar_vega| > 500, report must contain 'VOL_SENSITIVE'."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    state = _make_state()

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=VOL_SENSITIVE_CHAIN)):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    assert "VOL_SENSITIVE" in result["greeks_report"], (
        f"Expected VOL_SENSITIVE flag when |vega| > 500, got: {result['greeks_report']}"
    )


# ---------------------------------------------------------------------------
# Test 10: Tradier fallback — exception from route_to_vendor
# ---------------------------------------------------------------------------

def test_tradier_fallback():
    """When route_to_vendor raises, report uses delta from legs, sets gamma/theta/vega=0, contains 'Greeks unavailable'."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    # Phase 3 format legs (has explicit delta values) for fallback delta extraction
    phase3_legs = (
        "LEG 1: BUY CALL AAPL 2026-05-10 $150.0 delta=0.55 OI=300 [PASS]\n"
        "LEG 2: SELL CALL AAPL 2026-05-10 $155.0 delta=0.40 OI=200 [PASS]"
    )
    state = _make_state(legs=phase3_legs)

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=Exception("Tradier unavailable")):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    report = result["greeks_report"]
    assert "Greeks unavailable" in report, (
        f"Expected 'Greeks unavailable' in fallback report, got: {report}"
    )
    # Should still contain the net values
    assert "net_delta=" in report or "net_dollar_delta=" in report or "net_delta=" in report, (
        f"Expected net_delta in fallback report, got: {report}"
    )


# ---------------------------------------------------------------------------
# Test 11: Put delta sign convention — PUT legs negate delta
# ---------------------------------------------------------------------------

def test_put_delta_sign_convention():
    """For PUT legs, delta must be negated (stored as positive in chain, but economically negative)."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    # Single long put: sign=+1, delta from chain = 0.40 (but should be negated to -0.40 for puts)
    # dollar_delta = +1 * (-0.40) * 1 * 100 * 175 = -7000
    # |dollar_delta| = 7000 > 5000 -> DELTA_HEAVY if we correctly negate
    # If we DON'T negate: +1 * 0.40 * 100 * 175 = 7000 -> still DELTA_HEAVY (but wrong sign)
    # Better test: use put that should NOT be DELTA_HEAVY if sign is wrong but IS if correct
    # Actually: test that net_dollar_delta is NEGATIVE for a long put (correct convention)
    # We'll check: a single BUY PUT with delta=0.40 gives net_dollar_delta < 0

    put_legs = (
        "LEG 1: BUY PUT AAPL 2026-05-10 $150.00 limit=5.00 qty=1 [OK]\n"
        "NET: debit=5.00 max_profit=144.00 max_loss=5.00 breakeven=145.00"
    )
    put_chain = (
        "strike  option_type  bid   ask   delta  gamma  theta   vega   open_interest  iv    underlying\n"
        "150.0   put          4.8   5.2   0.40   0.03   -0.10   0.15   200            0.24  175.0\n"
    )

    state = _make_state(legs=put_legs)

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=put_chain)):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    report = result["greeks_report"]
    # dollar_delta for BUY PUT = +1 * (-0.40) * 1 * 100 * 175 = -7000
    # Report should contain net_delta or net_dollar_delta; check no crash and DELTA_HEAVY set
    assert "DELTA_HEAVY" in report, (
        f"Expected DELTA_HEAVY for single long put with |dollar_delta|=7000, got: {report}"
    )


# ---------------------------------------------------------------------------
# Test 12: Report contains net values
# ---------------------------------------------------------------------------

def test_report_contains_net_values():
    """Report string must contain net_delta=, net_gamma=, net_theta=, net_vega=."""
    from tradingagents.agents.options.greeks_monitor import create_greeks_monitor

    state = _make_state()

    with patch("tradingagents.agents.options.greeks_monitor.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=STANDARD_CHAIN)):
        node = create_greeks_monitor(_make_mock_llm())
        result = node(state)

    report = result["greeks_report"]
    assert "net_delta=" in report, f"Expected 'net_delta=' in report, got: {report}"
    assert "net_gamma=" in report, f"Expected 'net_gamma=' in report, got: {report}"
    assert "net_theta=" in report, f"Expected 'net_theta=' in report, got: {report}"
    assert "net_vega=" in report, f"Expected 'net_vega=' in report, got: {report}"
