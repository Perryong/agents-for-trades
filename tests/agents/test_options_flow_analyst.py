"""Unit tests for create_options_flow_analyst factory and helper functions.

All data layer (route_to_vendor) and LLM calls are mocked.
No live API calls are made in any test.
"""
import io
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers: build a mock LLM that works with (prompt | llm).invoke({}) chain pattern
# ---------------------------------------------------------------------------

def _make_mock_llm(report_content="mocked flow report"):
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

    return mock_llm, mock_response


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

VALID_CHAIN_STR = (
    "strike  option_type  volume  open_interest  iv  delta\n"
    "145.0   call         700     400            0.28  0.55\n"
    "150.0   call         200     300            0.26  0.45\n"
    "155.0   call         100     200            0.24  0.25\n"
    "145.0   put          400     350            0.32  -0.45\n"
    "140.0   put          200     250            0.35  -0.25\n"
    "135.0   put          100     200            0.38  -0.20\n"
)


def _make_route_side_effect(expirations=None, chain_str=VALID_CHAIN_STR):
    if expirations is None:
        expirations = ["2026-04-17", "2026-06-20"]

    def _side_effect(method, *args, **kwargs):
        if method == "get_options_expirations":
            return expirations
        elif method == "get_options_chain":
            return chain_str
        return ""

    return _side_effect


# ---------------------------------------------------------------------------
# Test 1: Factory returns a callable
# ---------------------------------------------------------------------------

def test_factory_returns_callable():
    """create_options_flow_analyst(llm) must return a callable."""
    from tradingagents.agents.options.options_flow_analyst import create_options_flow_analyst

    mock_llm, _ = _make_mock_llm()
    node = create_options_flow_analyst(mock_llm)
    assert callable(node), "Factory must return a callable node"


# ---------------------------------------------------------------------------
# Test 2: Node returns dict with options_flow_report key
# ---------------------------------------------------------------------------

def test_node_returns_options_flow_report():
    """Node must return a dict with 'options_flow_report' key containing a string."""
    from tradingagents.agents.options.options_flow_analyst import create_options_flow_analyst

    mock_llm, mock_response = _make_mock_llm("P/C Ratio: 1.00. Unusual Activity: 1 flagged. Net Flow: Call-dominated.")

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-03-31",
        "messages": [],
    }

    with patch("tradingagents.agents.options.options_flow_analyst.route_to_vendor",
               side_effect=_make_route_side_effect()):
        node = create_options_flow_analyst(mock_llm)
        result = node(state)

    assert isinstance(result, dict), "Node must return a dict"
    assert "options_flow_report" in result, "Return dict must contain 'options_flow_report' key"
    assert isinstance(result["options_flow_report"], str), "options_flow_report must be a string"


# ---------------------------------------------------------------------------
# Test 3: Unusual volume detection - volume > 2x OI flags as unusual
# ---------------------------------------------------------------------------

def test_unusual_volume_detected():
    """Contract with volume=1000, OI=400 is flagged as unusual (1000 > 2*400=800)."""
    from tradingagents.agents.options.options_flow_analyst import _compute_flow_metrics

    # 1000 > 2*400 => unusual
    chain_data = {
        "strike": [150.0, 155.0],
        "option_type": ["call", "call"],
        "volume": [1000, 200],
        "open_interest": [400, 300],
        "iv": [0.28, 0.26],
        "delta": [0.55, 0.45],
    }
    chain_df = pd.DataFrame(chain_data)

    metrics = _compute_flow_metrics(chain_df)

    assert metrics["unusual_count"] >= 1, (
        f"Expected at least 1 unusual contract (volume=1000 > 2*400=800), "
        f"got unusual_count={metrics['unusual_count']}"
    )


# ---------------------------------------------------------------------------
# Test 4: Unusual volume non-detection - volume <= 2x OI does NOT flag
# ---------------------------------------------------------------------------

def test_unusual_volume_not_detected():
    """Contract with volume=500, OI=400 is NOT flagged unusual (500 < 2*400=800)."""
    from tradingagents.agents.options.options_flow_analyst import _compute_flow_metrics

    chain_data = {
        "strike": [150.0],
        "option_type": ["call"],
        "volume": [500],
        "open_interest": [400],
        "iv": [0.28],
        "delta": [0.55],
    }
    chain_df = pd.DataFrame(chain_data)

    metrics = _compute_flow_metrics(chain_df)

    assert metrics["unusual_count"] == 0, (
        f"Expected 0 unusual contracts (volume=500 < 2*400=800), "
        f"got unusual_count={metrics['unusual_count']}"
    )


# ---------------------------------------------------------------------------
# Test 5: P/C ratio - put_vol=600, call_vol=400 → ratio = 1.50
# ---------------------------------------------------------------------------

def test_pc_ratio_normal():
    """P/C ratio = put_vol / call_vol = 600/400 = 1.50."""
    from tradingagents.agents.options.options_flow_analyst import _compute_flow_metrics

    chain_data = {
        "strike": [150.0, 145.0],
        "option_type": ["call", "put"],
        "volume": [400, 600],
        "open_interest": [300, 300],
        "iv": [0.28, 0.32],
        "delta": [0.55, -0.45],
    }
    chain_df = pd.DataFrame(chain_data)

    metrics = _compute_flow_metrics(chain_df)

    assert metrics["pc_ratio"] is not None, "P/C ratio should not be None when call volume > 0"
    assert abs(metrics["pc_ratio"] - 1.50) < 0.01, (
        f"Expected P/C ratio=1.50, got {metrics['pc_ratio']}"
    )


# ---------------------------------------------------------------------------
# Test 6: P/C ratio - call_vol=0 → ratio = None (division by zero guard)
# ---------------------------------------------------------------------------

def test_pc_ratio_zero_call_volume():
    """P/C ratio should be None when call_vol=0 (division by zero guard)."""
    from tradingagents.agents.options.options_flow_analyst import _compute_flow_metrics

    chain_data = {
        "strike": [145.0, 140.0],
        "option_type": ["put", "put"],
        "volume": [300, 200],
        "open_interest": [200, 150],
        "iv": [0.32, 0.35],
        "delta": [-0.45, -0.25],
    }
    chain_df = pd.DataFrame(chain_data)

    metrics = _compute_flow_metrics(chain_df)

    assert metrics["pc_ratio"] is None, (
        f"Expected P/C ratio=None when call_vol=0, got {metrics['pc_ratio']}"
    )


# ---------------------------------------------------------------------------
# Test 7: Net bias - call_vol=700, put_vol=300 → Call-dominated (70% call volume)
# ---------------------------------------------------------------------------

def test_net_bias_call_dominated():
    """call_vol=700, put_vol=300 → net_bias contains 'Call-dominated'."""
    from tradingagents.agents.options.options_flow_analyst import _compute_flow_metrics

    chain_data = {
        "strike": [150.0, 145.0],
        "option_type": ["call", "put"],
        "volume": [700, 300],
        "open_interest": [400, 350],
        "iv": [0.28, 0.32],
        "delta": [0.55, -0.45],
    }
    chain_df = pd.DataFrame(chain_data)

    metrics = _compute_flow_metrics(chain_df)

    assert "Call-dominated" in metrics["net_bias"], (
        f"Expected 'Call-dominated' in net_bias, got '{metrics['net_bias']}'"
    )
    assert "70%" in metrics["net_bias"], (
        f"Expected '70%' in net_bias label, got '{metrics['net_bias']}'"
    )


# ---------------------------------------------------------------------------
# Test 8: Net bias - call_vol=300, put_vol=700 → Put-dominated (70% put volume)
# ---------------------------------------------------------------------------

def test_net_bias_put_dominated():
    """call_vol=300, put_vol=700 → net_bias contains 'Put-dominated'."""
    from tradingagents.agents.options.options_flow_analyst import _compute_flow_metrics

    chain_data = {
        "strike": [150.0, 145.0],
        "option_type": ["call", "put"],
        "volume": [300, 700],
        "open_interest": [300, 400],
        "iv": [0.28, 0.32],
        "delta": [0.55, -0.45],
    }
    chain_df = pd.DataFrame(chain_data)

    metrics = _compute_flow_metrics(chain_df)

    assert "Put-dominated" in metrics["net_bias"], (
        f"Expected 'Put-dominated' in net_bias, got '{metrics['net_bias']}'"
    )
    assert "70%" in metrics["net_bias"], (
        f"Expected '70%' in net_bias label, got '{metrics['net_bias']}'"
    )


# ---------------------------------------------------------------------------
# Test 9: Net bias - call_vol=500, put_vol=500 → Balanced (50% calls, 50% puts)
# ---------------------------------------------------------------------------

def test_net_bias_balanced():
    """call_vol=500, put_vol=500 → net_bias contains 'Balanced'."""
    from tradingagents.agents.options.options_flow_analyst import _compute_flow_metrics

    chain_data = {
        "strike": [150.0, 145.0],
        "option_type": ["call", "put"],
        "volume": [500, 500],
        "open_interest": [300, 300],
        "iv": [0.28, 0.32],
        "delta": [0.55, -0.45],
    }
    chain_df = pd.DataFrame(chain_data)

    metrics = _compute_flow_metrics(chain_df)

    assert "Balanced" in metrics["net_bias"], (
        f"Expected 'Balanced' in net_bias, got '{metrics['net_bias']}'"
    )


# ---------------------------------------------------------------------------
# Test 10: Empty expirations list does NOT raise IndexError
# ---------------------------------------------------------------------------

def test_empty_expirations_no_crash():
    """Node must not raise IndexError when expirations list is empty;
    must return a report acknowledging missing data."""
    from tradingagents.agents.options.options_flow_analyst import create_options_flow_analyst

    mock_llm, mock_response = _make_mock_llm("No options data available for AAPL.")

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-03-31",
        "messages": [],
    }

    with patch("tradingagents.agents.options.options_flow_analyst.route_to_vendor",
               side_effect=_make_route_side_effect(expirations=[])):
        node = create_options_flow_analyst(mock_llm)
        # Must not raise IndexError or any other exception
        result = node(state)

    assert "options_flow_report" in result, (
        "Must still return options_flow_report even with empty expirations"
    )


# ---------------------------------------------------------------------------
# Test 11: Return dict does NOT contain "messages" key
# ---------------------------------------------------------------------------

def test_no_messages_written():
    """Return dict must NOT contain 'messages' key."""
    from tradingagents.agents.options.options_flow_analyst import create_options_flow_analyst

    mock_llm, mock_response = _make_mock_llm("test flow report")

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-03-31",
        "messages": [],
    }

    with patch("tradingagents.agents.options.options_flow_analyst.route_to_vendor",
               side_effect=_make_route_side_effect()):
        node = create_options_flow_analyst(mock_llm)
        result = node(state)

    assert "messages" not in result, (
        f"Return dict must NOT contain 'messages' key, got keys: {list(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Multi-bucket test helpers
# ---------------------------------------------------------------------------

def _make_route_side_effect_multi_bucket(
    expirations=None,
    chain_str=VALID_CHAIN_STR,
    fail_expiry=None,
):
    """Route side effect covering all 4 DTE buckets.

    expirations: list of expiry strings (default covers all 4 buckets for 2026-04-10)
    chain_str: chain data to return for successful fetches
    fail_expiry: if set, raise ValueError when get_options_chain is called for this expiry
    """
    if expirations is None:
        # Relative to trade_date="2026-04-10":
        #   2026-04-12 = 2 DTE  → SHORT (0-5)
        #   2026-04-20 = 10 DTE → WEEKLY (5-14)
        #   2026-05-10 = 30 DTE → MONTHLY (14-45)
        #   2026-06-15 = 66 DTE → LONGER (45-90)
        expirations = ["2026-04-12", "2026-04-20", "2026-05-10", "2026-06-15"]

    def _side_effect(method, *args, **kwargs):
        if method == "get_options_expirations":
            return expirations
        elif method == "get_options_chain":
            expiry_arg = args[1] if len(args) > 1 else None
            if fail_expiry is not None and expiry_arg == fail_expiry:
                raise ValueError(f"Simulated fetch failure for {expiry_arg}")
            return chain_str
        return ""

    return _side_effect


def _extract_llm_data_content(mock_llm):
    """Extract the data_content string passed to the LLM from mock call args.

    LangChain's RunnableSequence calls llm(ChatPromptValue) where the arg is a
    ChatPromptValue object with a .messages list. The last message is the
    HumanMessage whose .content is the data_content string.
    """
    assert mock_llm.call_args is not None, "LLM was never called"
    call_args = mock_llm.call_args
    # Positional arg[0] is the ChatPromptValue from LangChain's pipe operator
    prompt_value = call_args[0][0]
    # ChatPromptValue has .messages list; fall back to direct list if needed
    if hasattr(prompt_value, "messages"):
        messages = prompt_value.messages
    elif hasattr(prompt_value, "__iter__") and not isinstance(prompt_value, str):
        messages = list(prompt_value)
    else:
        return str(prompt_value)
    # The last message is the HumanMessage with data_content
    last_msg = messages[-1]
    if hasattr(last_msg, "content"):
        return last_msg.content
    return str(last_msg)


# ---------------------------------------------------------------------------
# Test 12: All 4 DTE bucket labels appear in LLM data_content
# ---------------------------------------------------------------------------

def test_multi_bucket_sections_present():
    """Node output includes all 4 DTE bucket labels in LLM data_content.

    Expirations cover all 4 buckets (relative to trade_date=2026-04-10):
      2026-04-12 = 2 DTE  → Short-term (0-5 DTE)
      2026-04-20 = 10 DTE → Weekly (5-14 DTE)
      2026-05-10 = 30 DTE → Monthly (14-45 DTE)
      2026-06-15 = 66 DTE → Longer-term (45-90 DTE)
    """
    from tradingagents.agents.options.options_flow_analyst import create_options_flow_analyst

    mock_llm, mock_response = _make_mock_llm("multi-bucket flow report")

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-04-10",
        "messages": [],
    }

    expirations = ["2026-04-12", "2026-04-20", "2026-05-10", "2026-06-15"]

    with patch("tradingagents.agents.options.options_flow_analyst.route_to_vendor",
               side_effect=_make_route_side_effect_multi_bucket(expirations=expirations)):
        node = create_options_flow_analyst(mock_llm)
        result = node(state)

    assert "options_flow_report" in result

    data_content = _extract_llm_data_content(mock_llm)

    expected_labels = [
        "Short-term (0-5 DTE)",
        "Weekly (5-14 DTE)",
        "Monthly (14-45 DTE)",
        "Longer-term (45-90 DTE)",
    ]
    for label in expected_labels:
        assert label in data_content, (
            f"Expected bucket label '{label}' in LLM data_content, but it was missing.\n"
            f"data_content snippet: {data_content[:500]}"
        )


# ---------------------------------------------------------------------------
# Test 13: Missing buckets are noted as "No data"
# ---------------------------------------------------------------------------

def test_missing_bucket_noted_as_no_data():
    """When only one expiry exists (SHORT bucket), other buckets show 'No data'.

    trade_date=2026-04-10, expirations=["2026-04-12"] (2 DTE → SHORT only).
    The remaining 3 buckets (WEEKLY, MONTHLY, LONGER) have no expiry → "No data".
    """
    from tradingagents.agents.options.options_flow_analyst import create_options_flow_analyst

    mock_llm, mock_response = _make_mock_llm("partial bucket flow report")

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-04-10",
        "messages": [],
    }

    with patch("tradingagents.agents.options.options_flow_analyst.route_to_vendor",
               side_effect=_make_route_side_effect_multi_bucket(expirations=["2026-04-12"])):
        node = create_options_flow_analyst(mock_llm)
        result = node(state)

    assert "options_flow_report" in result

    data_content = _extract_llm_data_content(mock_llm)

    assert "No data" in data_content or "No expirations available" in data_content, (
        f"Expected 'No data' or 'No expirations available' in data_content for missing buckets.\n"
        f"data_content snippet: {data_content[:600]}"
    )


# ---------------------------------------------------------------------------
# Test 14: Bucket fetch failure is isolated — node does NOT crash
# ---------------------------------------------------------------------------

def test_bucket_fetch_failure_isolated():
    """When one bucket's chain fetch raises ValueError, node does NOT crash.

    expirations cover all 4 buckets; route_to_vendor raises ValueError for
    get_options_chain when expiry is '2026-04-20' (WEEKLY bucket).
    Node must complete and return {"options_flow_report": ...}.
    """
    from tradingagents.agents.options.options_flow_analyst import create_options_flow_analyst

    mock_llm, mock_response = _make_mock_llm("partially degraded flow report")

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-04-10",
        "messages": [],
    }

    expirations = ["2026-04-12", "2026-04-20", "2026-05-10", "2026-06-15"]

    with patch("tradingagents.agents.options.options_flow_analyst.route_to_vendor",
               side_effect=_make_route_side_effect_multi_bucket(
                   expirations=expirations,
                   fail_expiry="2026-04-20",
               )):
        node = create_options_flow_analyst(mock_llm)
        # Must not raise any exception
        result = node(state)

    assert isinstance(result, dict), "Node must return a dict even with partial fetch failure"
    assert "options_flow_report" in result, (
        "Must return options_flow_report even when one bucket fetch fails"
    )
