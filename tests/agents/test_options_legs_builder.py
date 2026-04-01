"""Unit tests for create_options_legs_builder factory.

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
# Bull call spread:
#   State options_legs: LEG 1 BUY CALL AAPL 2026-05-10 $150.0 delta=0.30 OI=300 [PASS]
#                       LEG 2 SELL CALL AAPL 2026-05-10 $155.0 delta=0.22 OI=200 [PASS]
#   Chain:
#     150.0 call bid=8.00 ask=8.90 -> mid=8.45
#     155.0 call bid=4.80 ask=5.60 -> mid=5.20
#   net_debit = 8.45 - 5.20 = 3.25
#   max_profit = (155-150) - 3.25 = 1.75
#   max_loss   = 3.25
#   breakeven  = 150 + 3.25 = 153.25
# ---------------------------------------------------------------------------

BULL_CALL_LEGS_STR = (
    "LEG 1: BUY CALL AAPL 2026-05-10 $150.0 delta=0.30 OI=300 [PASS]\n"
    "LEG 2: SELL CALL AAPL 2026-05-10 $155.0 delta=0.22 OI=200 [PASS]"
)

BULL_CALL_CHAIN_STR = (
    "strike  option_type  bid    ask    volume  open_interest  iv     delta\n"
    "150.0   call         8.00   8.90   500     300            0.25   0.30\n"
    "155.0   call         4.80   5.60   400     200            0.23   0.22\n"
)

# Wide spread test: bid=7.00, ask=9.00 -> spread=2.00, mid=8.00, 2.00/8.00=0.25 > 0.10
WIDE_SPREAD_CHAIN_STR = (
    "strike  option_type  bid    ask    volume  open_interest  iv     delta\n"
    "150.0   call         7.00   9.00   500     300            0.25   0.30\n"
    "155.0   call         4.80   5.60   400     200            0.23   0.22\n"
)

# Narrow spread: bid=8.00, ask=8.90 -> spread=0.90, mid=8.45, 0.90/8.45=0.1065 > 0.10
# Need to ensure a truly narrow spread: bid=8.00, ask=8.40 -> spread=0.40, mid=8.20, 0.40/8.20=0.049 < 0.10
NARROW_SPREAD_CHAIN_STR = (
    "strike  option_type  bid    ask    volume  open_interest  iv     delta\n"
    "150.0   call         8.00   8.40   500     300            0.25   0.30\n"
    "155.0   call         4.80   5.00   400     200            0.23   0.22\n"
)

LONG_CALL_LEGS_STR = (
    "LEG 1: BUY CALL AAPL 2026-05-10 $150.0 delta=0.30 OI=300 [PASS]"
)

LONG_CALL_CHAIN_STR = (
    "strike  option_type  bid    ask    volume  open_interest  iv     delta\n"
    "150.0   call         8.00   8.90   500     300            0.25   0.30\n"
)


def _make_route_side_effect(chain_str=BULL_CALL_CHAIN_STR):
    def _side_effect(method, *args, **kwargs):
        if method == "get_options_chain":
            return chain_str
        return ""
    return _side_effect


def _make_bull_call_state():
    return {
        "company_of_interest": "AAPL",
        "trade_date": "2026-04-01",
        "options_strategy": "bull call spread",
        "options_legs": BULL_CALL_LEGS_STR,
        "messages": [],
    }


def _make_long_call_state():
    return {
        "company_of_interest": "AAPL",
        "trade_date": "2026-04-01",
        "options_strategy": "long call",
        "options_legs": LONG_CALL_LEGS_STR,
        "messages": [],
    }


# ---------------------------------------------------------------------------
# Test 1: Factory returns callable
# ---------------------------------------------------------------------------

def test_factory_returns_callable():
    """create_options_legs_builder(llm) must return a callable."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    node = create_options_legs_builder(_make_mock_llm())
    assert callable(node), "Factory must return a callable node"


# ---------------------------------------------------------------------------
# Test 2: Returns dict with options_legs key containing str
# ---------------------------------------------------------------------------

def test_returns_options_legs():
    """Node must return a dict with 'options_legs' key containing a string."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    state = _make_bull_call_state()

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    assert isinstance(result, dict), "Node must return a dict"
    assert "options_legs" in result, "Return dict must contain 'options_legs' key"
    assert isinstance(result["options_legs"], str), "options_legs must be a string"


# ---------------------------------------------------------------------------
# Test 3: No messages written
# ---------------------------------------------------------------------------

def test_no_messages_written():
    """Return dict must NOT contain 'messages' key."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    state = _make_bull_call_state()

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    assert "messages" not in result, (
        f"Return dict must NOT contain 'messages' key, got keys: {list(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 4: Output format per leg — contains limit= and qty=1
# ---------------------------------------------------------------------------

def test_output_format_per_leg():
    """Each leg line must contain 'limit=' and 'qty=1'."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    state = _make_bull_call_state()

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    legs_str = result["options_legs"]
    lines = [l for l in legs_str.split("\n") if l.startswith("LEG")]
    assert len(lines) >= 1, f"Expected at least one LEG line, got: {legs_str}"
    for line in lines:
        assert "limit=" in line, f"Expected 'limit=' in leg line: {line}"
        assert "qty=1" in line, f"Expected 'qty=1' in leg line: {line}"


# ---------------------------------------------------------------------------
# Test 5: Wide spread flag — WIDE_SPREAD when (ask-bid)/mid > 0.10
# ---------------------------------------------------------------------------

def test_wide_spread_flag():
    """When (ask-bid)/mid > 0.10, leg line must contain '[WIDE_SPREAD]'."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    state = _make_bull_call_state()

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect(WIDE_SPREAD_CHAIN_STR)), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    legs_str = result["options_legs"]
    assert "[WIDE_SPREAD]" in legs_str, (
        f"Expected [WIDE_SPREAD] for bid=7.00, ask=9.00 (spread/mid=0.25 > 0.10), got: {legs_str}"
    )


# ---------------------------------------------------------------------------
# Test 6: Narrow spread — [OK] when (ask-bid)/mid <= 0.10
# ---------------------------------------------------------------------------

def test_narrow_spread_ok():
    """When (ask-bid)/mid <= 0.10, leg line must contain '[OK]'."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    state = _make_bull_call_state()

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect(NARROW_SPREAD_CHAIN_STR)), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    legs_str = result["options_legs"]
    # Both legs should have narrow spread (bid=8.00 ask=8.40 -> 0.049 < 0.10)
    lines = [l for l in legs_str.split("\n") if l.startswith("LEG")]
    for line in lines:
        assert "[OK]" in line, (
            f"Expected [OK] for narrow spread (spread/mid < 0.10), got: {line}"
        )


# ---------------------------------------------------------------------------
# Test 7: NET summary line with debit=, max_profit=, max_loss=, breakeven=
# ---------------------------------------------------------------------------

def test_net_summary_line():
    """Output must contain 'NET:' line with debit=, max_profit=, max_loss=, breakeven=."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    state = _make_bull_call_state()

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    legs_str = result["options_legs"]
    assert "NET:" in legs_str, f"Expected 'NET:' line in output, got: {legs_str}"
    net_line = [l for l in legs_str.split("\n") if l.startswith("NET:")][0]
    assert "max_profit=" in net_line, f"Expected 'max_profit=' in NET line: {net_line}"
    assert "max_loss=" in net_line, f"Expected 'max_loss=' in NET line: {net_line}"
    assert "breakeven=" in net_line, f"Expected 'breakeven=' in NET line: {net_line}"
    # Either 'debit=' or 'credit=' must be present
    assert ("debit=" in net_line or "credit=" in net_line), (
        f"Expected 'debit=' or 'credit=' in NET line: {net_line}"
    )


# ---------------------------------------------------------------------------
# Test 8: Bull call spread payoff calculations
# ---------------------------------------------------------------------------

def test_bull_call_spread_payoff():
    """Bull call spread: max_profit=1.75, max_loss=3.25, breakeven=153.25."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    state = _make_bull_call_state()

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect(BULL_CALL_CHAIN_STR)), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    legs_str = result["options_legs"]
    net_line = [l for l in legs_str.split("\n") if l.startswith("NET:")][0]

    assert "1.75" in net_line, f"Expected max_profit=1.75 in NET line: {net_line}"
    assert "3.25" in net_line, f"Expected max_loss=3.25 (and debit=3.25) in NET line: {net_line}"
    assert "153.25" in net_line, f"Expected breakeven=153.25 in NET line: {net_line}"


# ---------------------------------------------------------------------------
# Test 9: Long call payoff
# ---------------------------------------------------------------------------

def test_long_call_payoff():
    """Long call: max_profit='unlimited', max_loss=net_debit, breakeven=strike+net_debit."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    state = _make_long_call_state()

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect(LONG_CALL_CHAIN_STR)), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    legs_str = result["options_legs"]
    # mid_150 = (8.00+8.90)/2 = 8.45
    # max_loss = 8.45, breakeven = 150 + 8.45 = 158.45
    net_line = [l for l in legs_str.split("\n") if l.startswith("NET:")][0]
    assert "unlimited" in net_line, f"Expected max_profit='unlimited' for long call, got: {net_line}"
    assert "8.45" in net_line, f"Expected max_loss=8.45 in NET line: {net_line}"
    assert "158.45" in net_line, f"Expected breakeven=158.45 in NET line: {net_line}"


# ---------------------------------------------------------------------------
# Test 10: Handles liquidity fail gracefully
# ---------------------------------------------------------------------------

def test_handles_liquidity_fail():
    """When options_legs contains '[LIQUIDITY FAIL]', return graceful message."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-04-01",
        "options_strategy": "bull call spread",
        "options_legs": (
            "No contracts satisfy delta=0.30 +/-0.05 within DTE [21,45] with OI>100. [LIQUIDITY FAIL]"
        ),
        "messages": [],
    }

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    assert isinstance(result, dict), "Must return a dict"
    assert "options_legs" in result, "Must return 'options_legs' key"
    # Should not crash and should return graceful message (not raise exception)
    legs_str = result["options_legs"]
    assert isinstance(legs_str, str), "options_legs must be a string"
    # Must not contain the crash output — just a graceful message
    assert "No order" in legs_str or "contract selection failed" in legs_str, (
        f"Expected graceful failure message, got: {legs_str}"
    )


# ---------------------------------------------------------------------------
# Test 11: Zero mid — no ZeroDivisionError when bid=0, ask=0
# ---------------------------------------------------------------------------

def test_zero_mid_wide_spread():
    """When bid=0 and ask=0 (mid=0), flag as [WIDE_SPREAD], not ZeroDivisionError."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    zero_mid_chain = (
        "strike  option_type  bid    ask    volume  open_interest  iv     delta\n"
        "150.0   call         0.00   0.00   0       300            0.25   0.30\n"
        "155.0   call         0.00   0.00   0       200            0.23   0.22\n"
    )

    state = _make_bull_call_state()

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect(zero_mid_chain)), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    legs_str = result["options_legs"]
    assert "[WIDE_SPREAD]" in legs_str, (
        f"Expected [WIDE_SPREAD] for zero mid (bid=ask=0), got: {legs_str}"
    )


# ---------------------------------------------------------------------------
# Test 12: Contract count fixed at 1 — every leg line contains qty=1
# ---------------------------------------------------------------------------

def test_contract_count_fixed_one():
    """Every LEG line must contain 'qty=1'."""
    from tradingagents.agents.options.options_legs_builder import create_options_legs_builder

    state = _make_bull_call_state()

    with patch("tradingagents.agents.options.options_legs_builder.route_to_vendor",
               side_effect=_make_route_side_effect()), \
         patch("tradingagents.agents.options.options_legs_builder.get_config",
               return_value={}):
        node = create_options_legs_builder(_make_mock_llm())
        result = node(state)

    legs_str = result["options_legs"]
    lines = [l for l in legs_str.split("\n") if l.startswith("LEG")]
    assert len(lines) >= 1, f"Expected at least one LEG line, got: {legs_str}"
    for line in lines:
        assert "qty=1" in line, f"Expected 'qty=1' in every LEG line, got: {line}"
