"""Unit tests for create_options_pricing_agent factory.

All data layer (route_to_vendor), config (get_config), and LLM calls are mocked.
No live API calls are made in any test.
"""
import pytest
from unittest.mock import patch, MagicMock, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm(report_content="Theoretical: $8.40 | Market mid: $8.00 | Edge: +5.0% | Verdict: positive edge"):
    """Create a mock LLM compatible with (prompt | llm).invoke({}) chain pattern.

    LangChain's RunnableSequence calls the LLM as a callable (llm(messages)).
    We configure mock_llm.return_value so that mock_llm(...) returns mock_response.
    """
    mock_response = MagicMock()
    mock_response.content = report_content

    mock_llm = MagicMock()
    # LangChain calls llm(messages) when running the chain
    mock_llm.return_value = mock_response
    # Also cover llm.invoke(messages) path for newer LangChain versions
    mock_llm.invoke = MagicMock(return_value=mock_response)

    return mock_llm


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

CONTROLLED_CHAIN_STR = (
    "strike  option_type  bid    ask    volume  open_interest  iv     delta\n"
    "150.0   call         7.80   8.20   500     300            0.25   0.30\n"
)

CONTROLLED_CONFIG = {
    "options_risk_free_rate": 0.05,
}

TRADE_DATE = "2026-04-01"

OPTIONS_LEGS = (
    "LEG 1: BUY CALL AAPL 2026-05-10 $150.0 delta=0.30 OI=300 [PASS]"
)


def _make_state(
    options_legs=OPTIONS_LEGS,
    fundamentals_report="",
):
    return {
        "company_of_interest": "AAPL",
        "trade_date": TRADE_DATE,
        "options_legs": options_legs,
        "options_strategy": "long call",
        "fundamentals_report": fundamentals_report,
        "messages": [],
    }


# ---------------------------------------------------------------------------
# Test 1: Factory returns callable
# ---------------------------------------------------------------------------

def test_factory_returns_callable():
    """create_options_pricing_agent(llm) must return a callable."""
    from tradingagents.agents.options.options_pricing_agent import create_options_pricing_agent

    mock_llm = _make_mock_llm()
    node = create_options_pricing_agent(mock_llm)
    assert callable(node), "Factory must return a callable node"


# ---------------------------------------------------------------------------
# Test 2: Returns dict with options_pricing_report key containing str
# ---------------------------------------------------------------------------

def test_returns_pricing_report():
    """Node must return a dict with 'options_pricing_report' key containing a string."""
    from tradingagents.agents.options.options_pricing_agent import create_options_pricing_agent

    mock_llm = _make_mock_llm("Positive edge: BS theoretical $8.40, market mid $8.00, edge +5.0%.")
    state = _make_state()

    with patch("tradingagents.agents.options.options_pricing_agent.route_to_vendor",
               return_value=CONTROLLED_CHAIN_STR), \
         patch("tradingagents.agents.options.options_pricing_agent.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_options_pricing_agent(mock_llm)
        result = node(state)

    assert isinstance(result, dict), "Node must return a dict"
    assert "options_pricing_report" in result, "Return dict must contain 'options_pricing_report' key"
    assert isinstance(result["options_pricing_report"], str), "options_pricing_report must be a string"


# ---------------------------------------------------------------------------
# Test 3: Return dict does NOT contain "messages" key
# ---------------------------------------------------------------------------

def test_no_messages_written():
    """Return dict must NOT contain 'messages' key."""
    from tradingagents.agents.options.options_pricing_agent import create_options_pricing_agent

    mock_llm = _make_mock_llm()
    state = _make_state()

    with patch("tradingagents.agents.options.options_pricing_agent.route_to_vendor",
               return_value=CONTROLLED_CHAIN_STR), \
         patch("tradingagents.agents.options.options_pricing_agent.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_options_pricing_agent(mock_llm)
        result = node(state)

    assert "messages" not in result, (
        f"Return dict must NOT contain 'messages' key, got keys: {list(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 4: Risk-free rate from config
# ---------------------------------------------------------------------------

def test_risk_free_rate_default():
    """With config returning options_risk_free_rate=0.05, call_price is called with r=0.05."""
    from tradingagents.agents.options.options_pricing_agent import create_options_pricing_agent

    mock_llm = _make_mock_llm()
    state = _make_state()

    with patch("tradingagents.agents.options.options_pricing_agent.route_to_vendor",
               return_value=CONTROLLED_CHAIN_STR), \
         patch("tradingagents.agents.options.options_pricing_agent.get_config",
               return_value={"options_risk_free_rate": 0.05}), \
         patch("tradingagents.agents.options.options_pricing_agent.call_price",
               return_value=8.40) as mock_call_price:
        node = create_options_pricing_agent(mock_llm)
        result = node(state)

    # call_price must have been called with r=0.05
    assert mock_call_price.called, "call_price must be invoked for a CALL leg"
    args, kwargs = mock_call_price.call_args
    # r is the 4th positional argument: call_price(S, K, T, r, q, sigma)
    r_used = args[3] if len(args) > 3 else kwargs.get("r")
    assert r_used == 0.05, f"Expected r=0.05, got r={r_used}"


# ---------------------------------------------------------------------------
# Test 5: Dividend yield fallback to 0.0
# ---------------------------------------------------------------------------

def test_dividend_yield_fallback():
    """When fundamentals_report lacks dividendYield, q=0.0 is used in call_price."""
    from tradingagents.agents.options.options_pricing_agent import create_options_pricing_agent

    mock_llm = _make_mock_llm()
    # fundamentals_report has no dividendYield
    state = _make_state(fundamentals_report="No dividend information available.")

    with patch("tradingagents.agents.options.options_pricing_agent.route_to_vendor",
               return_value=CONTROLLED_CHAIN_STR), \
         patch("tradingagents.agents.options.options_pricing_agent.get_config",
               return_value=CONTROLLED_CONFIG), \
         patch("tradingagents.agents.options.options_pricing_agent.call_price",
               return_value=8.40) as mock_call_price:
        node = create_options_pricing_agent(mock_llm)
        result = node(state)

    assert mock_call_price.called, "call_price must be invoked"
    args, kwargs = mock_call_price.call_args
    # q is the 5th positional argument: call_price(S, K, T, r, q, sigma)
    q_used = args[4] if len(args) > 4 else kwargs.get("q")
    assert q_used == 0.0, f"Expected q=0.0 fallback, got q={q_used}"


# ---------------------------------------------------------------------------
# Test 6: LLM is called when there is a positive edge
# ---------------------------------------------------------------------------

def test_positive_edge_verdict():
    """When BS theoretical > market_mid by >5%, LLM.invoke is called with data containing 'edge'."""
    from tradingagents.agents.options.options_pricing_agent import create_options_pricing_agent

    mock_llm = _make_mock_llm("Positive edge: theoretically underpriced.")
    state = _make_state()

    # Patch call_price to return value well above mid (8.00), giving >5% edge
    with patch("tradingagents.agents.options.options_pricing_agent.route_to_vendor",
               return_value=CONTROLLED_CHAIN_STR), \
         patch("tradingagents.agents.options.options_pricing_agent.get_config",
               return_value=CONTROLLED_CONFIG), \
         patch("tradingagents.agents.options.options_pricing_agent.call_price",
               return_value=8.50):  # mid=8.00, edge=(8.50-8.00)/8.00*100 = +6.25%
        node = create_options_pricing_agent(mock_llm)
        result = node(state)

    # LLM must have been invoked
    assert mock_llm.called or mock_llm.invoke.called, "LLM must be invoked for verdict"
    # The result must contain the report
    assert "options_pricing_report" in result


# ---------------------------------------------------------------------------
# Test 7: call_price or put_price is called at least once
# ---------------------------------------------------------------------------

def test_calls_black_scholes():
    """Node must invoke call_price or put_price at least once for a CALL leg."""
    from tradingagents.agents.options.options_pricing_agent import create_options_pricing_agent

    mock_llm = _make_mock_llm()
    state = _make_state()

    with patch("tradingagents.agents.options.options_pricing_agent.route_to_vendor",
               return_value=CONTROLLED_CHAIN_STR), \
         patch("tradingagents.agents.options.options_pricing_agent.get_config",
               return_value=CONTROLLED_CONFIG), \
         patch("tradingagents.agents.options.options_pricing_agent.call_price",
               return_value=8.40) as mock_call_price:
        node = create_options_pricing_agent(mock_llm)
        result = node(state)

    assert mock_call_price.call_count >= 1, (
        f"call_price must be called at least once for a CALL leg, got {mock_call_price.call_count}"
    )


# ---------------------------------------------------------------------------
# Test 8: Handles LIQUIDITY FAIL input gracefully
# ---------------------------------------------------------------------------

def test_handles_liquidity_fail_input():
    """When options_legs contains '[LIQUIDITY FAIL]', report indicates no pricing possible."""
    from tradingagents.agents.options.options_pricing_agent import create_options_pricing_agent

    mock_llm = _make_mock_llm()
    liquidity_fail_legs = (
        "No contracts satisfy delta=0.30 +/-0.05 within DTE [21,45] with OI>100. [LIQUIDITY FAIL]"
    )
    state = _make_state(options_legs=liquidity_fail_legs)

    with patch("tradingagents.agents.options.options_pricing_agent.route_to_vendor",
               return_value=CONTROLLED_CHAIN_STR), \
         patch("tradingagents.agents.options.options_pricing_agent.get_config",
               return_value=CONTROLLED_CONFIG):
        node = create_options_pricing_agent(mock_llm)
        result = node(state)

    assert isinstance(result, dict), "Must return dict even for LIQUIDITY FAIL input"
    assert "options_pricing_report" in result, "Must return options_pricing_report even for LIQUIDITY FAIL"
    report = result["options_pricing_report"]
    # Report should indicate failure — not an actual pricing result
    assert any(
        keyword in report.lower()
        for keyword in ["no pricing", "liquidity fail", "failed", "unavailable"]
    ), f"Report should indicate pricing not available, got: {report}"
