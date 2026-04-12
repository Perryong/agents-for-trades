"""Unit tests for create_strike_expiry_selector factory.

All data layer (route_to_vendor) and config (get_config) calls are mocked.
No live API calls are made in any test.
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
# trade_date = "2026-04-01"
# expirations = ["2026-04-25", "2026-05-10"]
#   DTE for "2026-04-25" = 24 days, center = (21+45)/2 = 33
#   |24-33| = 9, |39-33| = 6  => "2026-05-10" (DTE=39) is closer to center
# ---------------------------------------------------------------------------

CONTROLLED_CHAIN_STR = (
    "strike  option_type  volume  open_interest  iv     delta\n"
    "150.0   call         500     300            0.25   0.30\n"
    "145.0   call         400     200            0.27   0.22\n"
    "155.0   call         300     50             0.23   0.38\n"
    "145.0   put          400     250            0.28   -0.30\n"
    "140.0   put          300     150            0.30   -0.22\n"
)

CONTROLLED_CONFIG = {
    "options_delta_target": 0.30,
    "options_dte_window": [21, 45],
    "options_min_oi": 100,
}

TRADE_DATE = "2026-04-01"
EXPIRATIONS = ["2026-04-25", "2026-05-10"]  # DTE 24 and 39


def _make_route_side_effect(expirations=None, chain_str=CONTROLLED_CHAIN_STR):
    if expirations is None:
        expirations = EXPIRATIONS

    def _side_effect(method, *args, **kwargs):
        if method == "get_options_expirations":
            return expirations
        elif method == "get_options_chain":
            return chain_str
        return ""

    return _side_effect


def _make_state(strategy="long call -- bullish bias"):
    return {
        "company_of_interest": "AAPL",
        "trade_date": TRADE_DATE,
        "options_strategy": strategy,
        "messages": [],
    }


# ---------------------------------------------------------------------------
# Test 1: Factory returns callable
# ---------------------------------------------------------------------------

def test_factory_returns_callable():
    """create_strike_expiry_selector(llm) must return a callable."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    node = create_strike_expiry_selector(_make_mock_llm())
    assert callable(node), "Factory must return a callable node"


# ---------------------------------------------------------------------------
# Test 2: Node returns dict with options_legs key containing str
# ---------------------------------------------------------------------------

def test_node_returns_options_legs():
    """Node must return a dict with 'options_legs' key containing a string."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    state = _make_state()

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_strike_expiry_selector(_make_mock_llm())
        result = node(state)

    assert isinstance(result, dict), "Node must return a dict"
    assert "options_legs" in result, "Return dict must contain 'options_legs' key"
    assert isinstance(result["options_legs"], str), "options_legs must be a string"


# ---------------------------------------------------------------------------
# Test 3: No messages written
# ---------------------------------------------------------------------------

def test_no_messages_written():
    """Return dict must NOT contain 'messages' key."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    state = _make_state()

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_strike_expiry_selector(_make_mock_llm())
        result = node(state)

    assert "messages" not in result, (
        f"Return dict must NOT contain 'messages' key, got keys: {list(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 4: Delta band filtering - selects contract with delta=0.30 (within band)
# ---------------------------------------------------------------------------

def test_delta_band_filtering():
    """Contract at delta=0.30 should be selected; output contains '0.30'."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    state = _make_state("long call -- bullish bias")

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_strike_expiry_selector(_make_mock_llm())
        result = node(state)

    legs = result["options_legs"]
    assert "0.30" in legs, (
        f"Expected delta=0.30 in output for long call strategy, got: {legs}"
    )
    assert "[PASS]" in legs, f"Expected [PASS] marker in output, got: {legs}"


# ---------------------------------------------------------------------------
# Test 5: Expiry center selection - picks expiry closest to center of DTE window
# ---------------------------------------------------------------------------

def test_expiry_center_selection():
    """With expirations giving DTE 24 and 39, center=33, picks DTE=39 (closer)."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    state = _make_state("long call -- bullish bias")

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_strike_expiry_selector(_make_mock_llm())
        result = node(state)

    legs = result["options_legs"]
    # "2026-05-10" is DTE=39, closer to center=33 than "2026-04-25" (DTE=24)
    assert "2026-05-10" in legs, (
        f"Expected expiry 2026-05-10 (DTE=39, closer to center=33), got: {legs}"
    )


# ---------------------------------------------------------------------------
# Test 6: Liquidity fail - no delta match
# ---------------------------------------------------------------------------

def test_liquidity_fail_no_delta_match():
    """Chain with no contracts in delta band yields [LIQUIDITY FAIL]."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    # All deltas outside band (0.30 +/- 0.05 = [0.25, 0.35])
    no_match_chain = (
        "strike  option_type  volume  open_interest  iv     delta\n"
        "145.0   call         400     200            0.27   0.10\n"
        "155.0   call         300     200            0.23   0.50\n"
    )

    state = _make_state("long call -- bullish bias")

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=no_match_chain)), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_strike_expiry_selector(_make_mock_llm())
        result = node(state)

    assert "[LIQUIDITY FAIL]" in result["options_legs"], (
        f"Expected [LIQUIDITY FAIL] when no delta match, got: {result['options_legs']}"
    )


# ---------------------------------------------------------------------------
# Test 7: Liquidity fail - empty expirations
# ---------------------------------------------------------------------------

def test_liquidity_fail_no_expirations():
    """Empty expirations list yields [LIQUIDITY FAIL]."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    state = _make_state("long call -- bullish bias")

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=_make_route_side_effect(expirations=[])), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_strike_expiry_selector(_make_mock_llm())
        result = node(state)

    assert "[LIQUIDITY FAIL]" in result["options_legs"], (
        f"Expected [LIQUIDITY FAIL] with empty expirations, got: {result['options_legs']}"
    )


# ---------------------------------------------------------------------------
# Test 8: Liquidity fail - matching delta but OI too low
# ---------------------------------------------------------------------------

def test_liquidity_fail_low_oi():
    """Contracts matching delta but OI < min_oi yield [LIQUIDITY FAIL]."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    low_oi_chain = (
        "strike  option_type  volume  open_interest  iv     delta\n"
        "150.0   call         200     50             0.25   0.30\n"
        "155.0   call         100     40             0.23   0.32\n"
    )

    state = _make_state("long call -- bullish bias")

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=low_oi_chain)), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_strike_expiry_selector(_make_mock_llm())
        result = node(state)

    assert "[LIQUIDITY FAIL]" in result["options_legs"], (
        f"Expected [LIQUIDITY FAIL] when OI < min_oi, got: {result['options_legs']}"
    )


# ---------------------------------------------------------------------------
# Test 9: PASS marker present for valid contracts
# ---------------------------------------------------------------------------

def test_pass_marker_present():
    """Valid contract selection output contains [PASS]."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    state = _make_state("long call -- bullish bias")

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_strike_expiry_selector(_make_mock_llm())
        result = node(state)

    assert "[PASS]" in result["options_legs"], (
        f"Expected [PASS] marker for valid contracts, got: {result['options_legs']}"
    )


# ---------------------------------------------------------------------------
# Test 10: Put delta sign convention - abs(delta) used for puts
# ---------------------------------------------------------------------------

def test_put_delta_sign_convention():
    """Put at delta=-0.30 should be found using abs(delta) filter."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    state = _make_state("long put -- bearish bias")

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_strike_expiry_selector(_make_mock_llm())
        result = node(state)

    legs = result["options_legs"]
    assert "[PASS]" in legs, (
        f"Expected [PASS] for put with delta=-0.30 (abs=0.30), got: {legs}"
    )
    assert "[LIQUIDITY FAIL]" not in legs, (
        f"Expected no LIQUIDITY FAIL for valid put contract, got: {legs}"
    )


# ---------------------------------------------------------------------------
# Test 11: Multi-leg spread - bull call spread has LEG 1 and LEG 2
# ---------------------------------------------------------------------------

def test_multi_leg_spread():
    """Bull call spread strategy output contains LEG 1 (buy) and LEG 2 (sell)."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector

    # Need a chain with two distinct call strikes in range
    spread_chain = (
        "strike  option_type  volume  open_interest  iv     delta\n"
        "150.0   call         500     300            0.25   0.30\n"
        "145.0   call         400     200            0.27   0.22\n"
        "155.0   call         300     200            0.23   0.38\n"
        "140.0   call         200     150            0.29   0.18\n"
    )

    state = _make_state("bull call spread -- moderate bullish")

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=_make_route_side_effect(chain_str=spread_chain)), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_strike_expiry_selector(_make_mock_llm())
        result = node(state)

    legs = result["options_legs"]
    assert "LEG 1" in legs, f"Expected LEG 1 in spread output, got: {legs}"
    assert "LEG 2" in legs, f"Expected LEG 2 in spread output, got: {legs}"


# ---------------------------------------------------------------------------
# Test 12: Strike/expiry selector emits anchor_strike, width, near_expiry, far_expiry
# ---------------------------------------------------------------------------

def test_anchor_width_output():
    """Strike/expiry selector must return anchor_strike, width, near_expiry, far_expiry keys."""
    from tradingagents.agents.options.strike_expiry_selector import create_strike_expiry_selector
    from unittest.mock import patch, MagicMock

    # Mock expirations
    mock_expirations = ["2026-05-10", "2026-06-20"]

    # Mock chain data
    chain_str = (
        "# SPOT:150.0\n"
        "strike  option_type  bid    ask    volume  open_interest  delta\n"
        "150.0   call         8.00   8.90   500     300            0.30\n"
        "155.0   call         4.80   5.60   400     200            0.22\n"
        "145.0   put          3.50   4.20   350     250            -0.28\n"
    )

    def route_side_effect(method, *args, **kwargs):
        if method == "get_options_expirations":
            return mock_expirations
        if method == "get_options_chain":
            return chain_str
        return ""

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-04-12",
        "options_strategy": "long call",
        "messages": [],
    }

    with patch("tradingagents.agents.options.strike_expiry_selector.route_to_vendor",
               side_effect=route_side_effect), \
         patch("tradingagents.agents.options.strike_expiry_selector.get_config",
               return_value={"options_delta_target": 0.30, "options_min_oi": 100}):
        node = create_strike_expiry_selector(MagicMock())
        result = node(state)

    assert "anchor_strike" in result, f"Missing anchor_strike key, got keys: {list(result.keys())}"
    assert "width" in result, f"Missing width key"
    assert "near_expiry" in result, f"Missing near_expiry key"
    assert "far_expiry" in result, f"Missing far_expiry key"
    # anchor_strike should be a float when legs were found
    if result["anchor_strike"] is not None:
        assert isinstance(result["anchor_strike"], float), f"anchor_strike must be float, got {type(result['anchor_strike'])}"
