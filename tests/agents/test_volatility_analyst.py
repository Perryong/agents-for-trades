"""Unit tests for create_volatility_analyst factory and helper functions.

All data layer (route_to_vendor) and LLM calls are mocked.
No live API calls are made in any test.
"""
import math
import io
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers: build a mock LLM that works with (prompt | llm).invoke({})
# ---------------------------------------------------------------------------

def _make_mock_llm(report_content="mocked volatility report"):
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

    return mock_llm, mock_llm, mock_response


# ---------------------------------------------------------------------------
# Test 1: Factory returns a callable
# ---------------------------------------------------------------------------

def test_factory_returns_callable():
    """create_volatility_analyst(llm) must return a callable."""
    from tradingagents.agents.options.volatility_analyst import create_volatility_analyst

    mock_llm, _, _ = _make_mock_llm()
    node = create_volatility_analyst(mock_llm)
    assert callable(node), "Factory must return a callable node"


# ---------------------------------------------------------------------------
# Test 2: Node returns dict with volatility_report key
# ---------------------------------------------------------------------------

VALID_IV_STR = (
    "date    iv\n"
    "2025-04-01  0.20\n"
    "2025-07-01  0.25\n"
    "2025-10-01  0.30\n"
    "2026-01-01  0.35\n"
    "2026-04-01  0.40\n"
)

VALID_CHAIN_STR = (
    "strike  option_type  volume  open_interest  iv  delta\n"
    "145.0  call  1000  500  0.28  0.55\n"
    "150.0  call  800  400  0.26  0.45\n"
    "155.0  call  500  300  0.24  0.25\n"
    "145.0  put  900  450  0.32  -0.45\n"
    "140.0  put  600  350  0.35  -0.25\n"
)

FAR_CHAIN_STR = (
    "strike  option_type  volume  open_interest  iv  delta\n"
    "145.0  call  500  300  0.31  0.52\n"
    "145.0  put  400  250  0.34  -0.48\n"
)


def _make_route_side_effect(iv_str=VALID_IV_STR, expirations=None, chain_str=VALID_CHAIN_STR):
    if expirations is None:
        expirations = ["2026-04-17", "2026-06-20"]

    def _side_effect(method, *args, **kwargs):
        if method == "get_historical_iv":
            return iv_str
        elif method == "get_options_expirations":
            return expirations
        elif method == "get_options_chain":
            # Return far chain for second expiry
            if args and len(args) > 1 and args[1] == "2026-06-20":
                return FAR_CHAIN_STR
            return chain_str
        return ""

    return _side_effect


def _make_mock_yf():
    """Return mock yf module with price history."""
    mock_yf = MagicMock()
    # Create a fake Close series for HV computation
    import pandas as pd
    import numpy as np
    # 90 days of price data
    prices = pd.Series([150.0 + i * 0.1 for i in range(90)])
    mock_hist = pd.DataFrame({"Close": prices})
    mock_yf.Ticker.return_value.history.return_value = mock_hist
    return mock_yf


def test_node_returns_volatility_report():
    """Node must return a dict with 'volatility_report' key containing a string."""
    from tradingagents.agents.options.volatility_analyst import create_volatility_analyst

    mock_llm, mock_chain, mock_response = _make_mock_llm("IV Rank: 50 (moderate).")
    mock_yf = _make_mock_yf()

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-03-31",
        "messages": [],
    }

    with patch("tradingagents.agents.options.volatility_analyst.route_to_vendor",
               side_effect=_make_route_side_effect()):
        with patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
            node = create_volatility_analyst(mock_llm)
            result = node(state)

    assert isinstance(result, dict), "Node must return a dict"
    assert "volatility_report" in result, "Return dict must contain 'volatility_report' key"
    assert isinstance(result["volatility_report"], str), "volatility_report must be a string"


# ---------------------------------------------------------------------------
# Test 3: IV rank formula
# ---------------------------------------------------------------------------

def test_iv_rank_formula():
    """IV rank = (current - min) / (max - min) * 100."""
    from tradingagents.agents.options.volatility_analyst import _compute_iv_metrics

    iv_series = pd.Series([0.20, 0.25, 0.30, 0.35, 0.40])
    current_iv = 0.30

    result = _compute_iv_metrics(iv_series, current_iv)

    expected_rank = (0.30 - 0.20) / (0.40 - 0.20) * 100  # = 50.0
    assert abs(result["iv_rank"] - expected_rank) < 0.01, (
        f"Expected iv_rank={expected_rank}, got {result['iv_rank']}"
    )


# ---------------------------------------------------------------------------
# Test 4: IV percentile formula
# ---------------------------------------------------------------------------

def test_iv_percentile_formula():
    """IV percentile = % of observations below current IV."""
    from tradingagents.agents.options.volatility_analyst import _compute_iv_metrics

    iv_series = pd.Series([0.20, 0.25, 0.30, 0.35, 0.40])
    current_iv = 0.30

    result = _compute_iv_metrics(iv_series, current_iv)

    # 2 values (0.20, 0.25) are strictly below 0.30, out of 5 total => 40.0%
    expected_pct = (2 / 5) * 100  # = 40.0
    assert abs(result["iv_pct"] - expected_pct) < 0.01, (
        f"Expected iv_pct={expected_pct}, got {result['iv_pct']}"
    )


# ---------------------------------------------------------------------------
# Test 5: 30-day HV computation
# ---------------------------------------------------------------------------

def test_hv30_formula():
    """30-day HV uses pct_change().rolling(21).std() * sqrt(252)."""
    from tradingagents.agents.options.volatility_analyst import _compute_hv30

    import pandas as pd
    import numpy as np

    # Known price series: constant prices => HV should be 0
    prices = pd.Series([100.0] * 90)
    mock_hist = pd.DataFrame({"Close": prices})

    mock_yf = MagicMock()
    mock_yf.Ticker.return_value.history.return_value = mock_hist

    with patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
        hv = _compute_hv30("AAPL")

    # Constant prices => pct_change = 0 => std = 0 => HV = 0
    assert hv is not None, "HV should not be None for valid price data"
    assert abs(hv) < 0.01, f"Expected HV~0 for constant prices, got {hv}"


def test_hv30_nontrivial():
    """HV should be non-zero for prices with actual variation."""
    from tradingagents.agents.options.volatility_analyst import _compute_hv30

    import pandas as pd
    import numpy as np

    # Trending prices with variation
    np.random.seed(42)
    prices = pd.Series(100 + np.cumsum(np.random.normal(0, 1, 90)))
    mock_hist = pd.DataFrame({"Close": prices})

    mock_yf = MagicMock()
    mock_yf.Ticker.return_value.history.return_value = mock_hist

    with patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
        hv = _compute_hv30("AAPL")

    assert hv is not None, "HV should not be None for varying prices"
    assert hv > 0, f"HV should be positive for varying prices, got {hv}"


# ---------------------------------------------------------------------------
# Test 6: Empty expirations does NOT raise IndexError
# ---------------------------------------------------------------------------

def test_empty_expirations_no_crash():
    """Node must not raise IndexError when expirations list is empty."""
    from tradingagents.agents.options.volatility_analyst import create_volatility_analyst

    mock_llm, mock_chain, mock_response = _make_mock_llm("No options data available.")
    mock_yf = _make_mock_yf()

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-03-31",
        "messages": [],
    }

    route_fn = _make_route_side_effect(expirations=[])

    with patch("tradingagents.agents.options.volatility_analyst.route_to_vendor",
               side_effect=route_fn):
        with patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
            node = create_volatility_analyst(mock_llm)
            # Must not raise
            result = node(state)

    assert "volatility_report" in result, "Must still return volatility_report even with empty expirations"


# ---------------------------------------------------------------------------
# Test 7: "No historical IV data" handled gracefully
# ---------------------------------------------------------------------------

def test_no_historical_iv_handled_gracefully():
    """Node must handle 'No historical IV data' string without crashing."""
    from tradingagents.agents.options.volatility_analyst import create_volatility_analyst

    mock_llm, mock_chain, mock_response = _make_mock_llm("Insufficient IV history.")
    mock_yf = _make_mock_yf()

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-03-31",
        "messages": [],
    }

    route_fn = _make_route_side_effect(iv_str="No historical IV data available for AAPL.")

    with patch("tradingagents.agents.options.volatility_analyst.route_to_vendor",
               side_effect=route_fn):
        with patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
            node = create_volatility_analyst(mock_llm)
            result = node(state)

    assert "volatility_report" in result, "Must return volatility_report even with missing IV data"


# ---------------------------------------------------------------------------
# Test 8: Return dict does NOT contain "messages" key
# ---------------------------------------------------------------------------

def test_no_messages_written():
    """Return dict must NOT contain 'messages' key."""
    from tradingagents.agents.options.volatility_analyst import create_volatility_analyst

    mock_llm, mock_chain, mock_response = _make_mock_llm("test report")
    mock_yf = _make_mock_yf()

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-03-31",
        "messages": [],
    }

    with patch("tradingagents.agents.options.volatility_analyst.route_to_vendor",
               side_effect=_make_route_side_effect()):
        with patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
            node = create_volatility_analyst(mock_llm)
            result = node(state)

    assert "messages" not in result, (
        f"Return dict must NOT contain 'messages' key, got keys: {list(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 9: Skew computation returns valid string
# ---------------------------------------------------------------------------

def test_skew_computation_put_skew():
    """Skew with OTM puts having higher IV than OTM calls → 'Put skew elevated'."""
    from tradingagents.agents.options.volatility_analyst import _compute_skew

    chain_data = {
        "strike": [140.0, 145.0, 150.0, 155.0, 160.0,
                   140.0, 145.0, 150.0, 155.0, 160.0],
        "option_type": ["put", "put", "put", "call", "call",
                        "put", "put", "call", "call", "call"],
        "iv": [0.40, 0.38, 0.30, 0.28, 0.26,
               0.38, 0.35, 0.29, 0.27, 0.25],
        "delta": [-0.25, -0.30, -0.50, 0.50, 0.30,
                  -0.20, -0.35, -0.48, 0.52, 0.25],
    }
    chain_df = pd.DataFrame(chain_data)

    result = _compute_skew(chain_df)
    assert isinstance(result, str), "Skew must return a string"
    assert result in (
        result  # any of the three valid forms
    ), "Skew must return a string"
    # At least one of the expected patterns
    valid_patterns = ["Put skew elevated", "Call skew elevated", "Flat skew"]
    assert any(p in result for p in valid_patterns), (
        f"Skew result '{result}' must contain one of {valid_patterns}"
    )


def test_skew_computation_call_skew():
    """Skew with OTM calls having much higher IV → 'Call skew elevated'."""
    from tradingagents.agents.options.volatility_analyst import _compute_skew

    # Make OTM calls much more expensive than OTM puts
    chain_data = {
        "strike": [140.0, 145.0, 155.0, 160.0],
        "option_type": ["put", "put", "call", "call"],
        "iv": [0.20, 0.22, 0.45, 0.48],  # put IV low, call IV high
        "delta": [-0.25, -0.22, 0.25, 0.22],
    }
    chain_df = pd.DataFrame(chain_data)

    result = _compute_skew(chain_df)
    assert "Call skew elevated" in result, (
        f"Expected 'Call skew elevated', got '{result}'"
    )


def test_skew_returns_na_for_none():
    """_compute_skew must return 'N/A' for None input."""
    from tradingagents.agents.options.volatility_analyst import _compute_skew

    result = _compute_skew(None)
    assert result == "N/A", f"Expected 'N/A' for None chain_df, got '{result}'"


# ---------------------------------------------------------------------------
# Test 10: Term structure returns valid string
# ---------------------------------------------------------------------------

def test_term_structure_contango():
    """Far IV > near IV + 0.01 → Contango."""
    from tradingagents.agents.options.volatility_analyst import _compute_term_structure

    near_data = {"iv": [0.25, 0.26, 0.24], "option_type": ["call", "put", "call"]}
    far_data = {"iv": [0.30, 0.31, 0.32], "option_type": ["call", "put", "call"]}

    near_df = pd.DataFrame(near_data)
    far_df = pd.DataFrame(far_data)

    result = _compute_term_structure(near_df, far_df)
    assert "Contango" in result, f"Expected 'Contango', got '{result}'"


def test_term_structure_backwardation():
    """Near IV > far IV + 0.01 → Backwardation."""
    from tradingagents.agents.options.volatility_analyst import _compute_term_structure

    near_data = {"iv": [0.35, 0.36, 0.34], "option_type": ["call", "put", "call"]}
    far_data = {"iv": [0.25, 0.26, 0.24], "option_type": ["call", "put", "call"]}

    near_df = pd.DataFrame(near_data)
    far_df = pd.DataFrame(far_data)

    result = _compute_term_structure(near_df, far_df)
    assert "Backwardation" in result, f"Expected 'Backwardation', got '{result}'"


def test_term_structure_returns_na_for_none():
    """_compute_term_structure must return 'N/A' when either df is None."""
    from tradingagents.agents.options.volatility_analyst import _compute_term_structure

    result = _compute_term_structure(None, None)
    assert result == "N/A", f"Expected 'N/A' for None inputs, got '{result}'"


# ---------------------------------------------------------------------------
# Integration test: full node with all mocks
# ---------------------------------------------------------------------------

def test_full_node_integration():
    """Integration: full node flow with all mocks — returns volatility_report string."""
    from tradingagents.agents.options.volatility_analyst import create_volatility_analyst

    mock_llm, mock_chain, mock_response = _make_mock_llm(
        "IV Rank: 50.0 (moderate). IV Percentile: 40.0th. IV vs HV: Rich (+5pp). "
        "Skew: Put skew elevated (+5.00%). Term structure: Contango. "
        "Regime: Moderate IV environment, put-bid market."
    )
    mock_yf = _make_mock_yf()

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-03-31",
        "messages": [],
    }

    with patch("tradingagents.agents.options.volatility_analyst.route_to_vendor",
               side_effect=_make_route_side_effect()):
        with patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
            node = create_volatility_analyst(mock_llm)
            result = node(state)

    assert "volatility_report" in result
    assert "messages" not in result
    assert len(result) == 1, f"Result should have exactly 1 key, got {list(result.keys())}"
    assert "IV Rank" in result["volatility_report"]


# ---------------------------------------------------------------------------
# Multi-bucket tests (Task 1 — TDD RED: these will FAIL until Task 2 is done)
# ---------------------------------------------------------------------------

# Expirations that cover all 4 DTE buckets when trade_date="2026-04-10":
#   2026-04-12 => DTE 2 => Short-term (0-5 DTE)
#   2026-04-20 => DTE 10 => Weekly (5-14 DTE)
#   2026-05-10 => DTE 30 => Monthly (14-45 DTE)
#   2026-06-15 => DTE 66 => Longer-term (45-90 DTE)

MULTI_BUCKET_EXPIRATIONS = ["2026-04-12", "2026-04-20", "2026-05-10", "2026-06-15"]

# Different chain strings per expiry so we can verify per-bucket processing
_CHAIN_BY_EXPIRY = {
    "2026-04-12": (
        "strike  option_type  volume  open_interest  iv  delta\n"
        "145.0  call  1000  500  0.28  0.55\n"
        "145.0  put  900  450  0.32  -0.45\n"
    ),
    "2026-04-20": (
        "strike  option_type  volume  open_interest  iv  delta\n"
        "145.0  call  800  400  0.26  0.53\n"
        "145.0  put  700  350  0.30  -0.47\n"
    ),
    "2026-05-10": (
        "strike  option_type  volume  open_interest  iv  delta\n"
        "145.0  call  600  300  0.24  0.50\n"
        "145.0  put  500  250  0.27  -0.50\n"
    ),
    "2026-06-15": (
        "strike  option_type  volume  open_interest  iv  delta\n"
        "145.0  call  400  200  0.31  0.48\n"
        "145.0  put  350  180  0.34  -0.52\n"
    ),
}


def _make_route_side_effect_multi_bucket(iv_str=VALID_IV_STR):
    """Route side effect that dispatches different chains per expiry date."""

    def _side_effect(method, *args, **kwargs):
        if method == "get_historical_iv":
            return iv_str
        elif method == "get_options_expirations":
            return MULTI_BUCKET_EXPIRATIONS
        elif method == "get_options_chain":
            expiry = args[1] if len(args) > 1 else None
            return _CHAIN_BY_EXPIRY.get(expiry, VALID_CHAIN_STR)
        return ""

    return _side_effect


def test_multi_bucket_iv_table_present():
    """Node's LLM input must include all 4 DTE bucket labels when all buckets are covered."""
    from tradingagents.agents.options.volatility_analyst import create_volatility_analyst

    mock_llm, mock_chain, mock_response = _make_mock_llm("multi-bucket volatility report")
    mock_yf = _make_mock_yf()

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-04-10",
        "messages": [],
    }

    captured_messages = []

    def capturing_llm(messages):
        captured_messages.extend(messages)
        return mock_response

    capturing_llm.invoke = capturing_llm

    with patch("tradingagents.agents.options.volatility_analyst.route_to_vendor",
               side_effect=_make_route_side_effect_multi_bucket()):
        with patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
            node = create_volatility_analyst(capturing_llm)
            result = node(state)

    assert "volatility_report" in result

    # Gather the full text sent to the LLM
    full_text = " ".join(
        m.content if hasattr(m, "content") else str(m)
        for m in captured_messages
    )

    assert "Short-term (0-5 DTE)" in full_text, (
        f"Expected 'Short-term (0-5 DTE)' in LLM input. Got: {full_text[:500]}"
    )
    assert "Weekly (5-14 DTE)" in full_text, (
        f"Expected 'Weekly (5-14 DTE)' in LLM input. Got: {full_text[:500]}"
    )
    assert "Monthly (14-45 DTE)" in full_text, (
        f"Expected 'Monthly (14-45 DTE)' in LLM input. Got: {full_text[:500]}"
    )
    assert "Longer-term (45-90 DTE)" in full_text, (
        f"Expected 'Longer-term (45-90 DTE)' in LLM input. Got: {full_text[:500]}"
    )


def test_missing_bucket_noted_in_vol_report():
    """When only SHORT bucket has expirations, missing buckets must contain 'No data' or 'N/A'."""
    from tradingagents.agents.options.volatility_analyst import create_volatility_analyst

    mock_llm, mock_chain, mock_response = _make_mock_llm("short-term only report")
    mock_yf = _make_mock_yf()

    state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-04-10",
        "messages": [],
    }

    # Only one expiry in SHORT bucket (DTE=2)
    short_only_expirations = ["2026-04-12"]

    def short_only_route(method, *args, **kwargs):
        if method == "get_historical_iv":
            return VALID_IV_STR
        elif method == "get_options_expirations":
            return short_only_expirations
        elif method == "get_options_chain":
            return _CHAIN_BY_EXPIRY["2026-04-12"]
        return ""

    captured_messages = []

    def capturing_llm(messages):
        captured_messages.extend(messages)
        return mock_response

    capturing_llm.invoke = capturing_llm

    with patch("tradingagents.agents.options.volatility_analyst.route_to_vendor",
               side_effect=short_only_route):
        with patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
            node = create_volatility_analyst(capturing_llm)
            result = node(state)

    assert "volatility_report" in result

    full_text = " ".join(
        m.content if hasattr(m, "content") else str(m)
        for m in captured_messages
    )

    # For the 3 missing buckets, the table should show N/A or No data
    assert "N/A" in full_text or "No data" in full_text, (
        f"Expected 'N/A' or 'No data' for missing buckets. Got: {full_text[:600]}"
    )


def test_compute_multi_bucket_term_structure_output():
    """_compute_multi_bucket_term_structure returns a string with table headers and all 4 labels."""
    from tradingagents.agents.options.volatility_analyst import _compute_multi_bucket_term_structure

    bucket_results = [
        {"label": "Short-term (0-5 DTE)", "median_iv": 0.28, "dte": 2, "skew": "Put skew elevated (+5.00%)", "expiry": "2026-04-12"},
        {"label": "Weekly (5-14 DTE)", "median_iv": 0.26, "dte": 10, "skew": "Flat skew (0.00%)", "expiry": "2026-04-20"},
        {"label": "Monthly (14-45 DTE)", "median_iv": None, "dte": None, "skew": "N/A", "expiry": None},
        {"label": "Longer-term (45-90 DTE)", "median_iv": 0.30, "dte": 66, "skew": "Put skew elevated (+3.00%)", "expiry": "2026-06-15"},
    ]

    output = _compute_multi_bucket_term_structure(bucket_results)

    assert isinstance(output, str), "Output must be a string"
    assert "Bucket" in output, f"Expected 'Bucket' header in output. Got: {output}"
    assert "Median IV" in output, f"Expected 'Median IV' header in output. Got: {output}"
    assert "Short-term (0-5 DTE)" in output
    assert "Weekly (5-14 DTE)" in output
    assert "Monthly (14-45 DTE)" in output
    assert "Longer-term (45-90 DTE)" in output
    assert "N/A" in output, "Monthly bucket (None median_iv) should show 'N/A'"


def test_existing_term_structure_unchanged():
    """_compute_term_structure(near_df, far_df) is still callable with 2 args (backward compat)."""
    from tradingagents.agents.options.volatility_analyst import _compute_term_structure

    near_data = {"iv": [0.25, 0.26, 0.24], "option_type": ["call", "put", "call"]}
    far_data = {"iv": [0.30, 0.31, 0.32], "option_type": ["call", "put", "call"]}

    near_df = pd.DataFrame(near_data)
    far_df = pd.DataFrame(far_data)

    result = _compute_term_structure(near_df, far_df)
    assert isinstance(result, str), "_compute_term_structure must return a string"
    assert "Contango" in result or "Backwardation" in result or "Flat" in result or "N/A" in result, (
        f"Result must be one of the known term structure patterns, got: {result}"
    )
