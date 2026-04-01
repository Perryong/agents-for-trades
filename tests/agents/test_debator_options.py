"""Unit tests for options-aware debator agents.

Verifies that all three debator agents (aggressive, conservative, neutral)
include an OPTIONS RISK ASSESSMENT block when options_legs is non-empty,
and produce no changes when options_legs is empty (equity-only mode).

No live LLM calls are made — LLM is mocked via MagicMock.
"""
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm(content="Analyst response"):
    """Create a mock LLM where llm.invoke(prompt) returns a mock with .content."""
    mock_response = MagicMock()
    mock_response.content = content

    mock_llm = MagicMock()
    mock_llm.invoke = MagicMock(return_value=mock_response)

    return mock_llm


# ---------------------------------------------------------------------------
# State fixtures
# ---------------------------------------------------------------------------

def _make_state(options_legs="LEG 1: BUY CALL AAPL 2026-05-10 $150 delta=0.30 OI=300 [PASS]"):
    return {
        "market_report": "market data",
        "sentiment_report": "sentiment data",
        "news_report": "news data",
        "fundamentals_report": "fundamentals data",
        "trader_investment_plan": "Buy AAPL",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
        "options_strategy": "long call",
        "options_legs": options_legs,
        "options_pricing_report": "Edge: +5%",
        "greeks_report": "Net delta: $2000, Flags: none",
        "volatility_report": "IV rank 45, regime normal",
        "options_flow_report": "Unusual call volume detected",
    }


def _make_equity_only_state():
    """State fixture for equity-only mode — all options fields are empty."""
    state = _make_state(options_legs="")
    state["options_strategy"] = ""
    state["options_pricing_report"] = ""
    state["greeks_report"] = ""
    state["volatility_report"] = ""
    state["options_flow_report"] = ""
    return state


def _get_invoked_prompt(mock_llm):
    """Extract the prompt string passed to llm.invoke() from call args."""
    assert mock_llm.invoke.called, "llm.invoke() was never called"
    args, kwargs = mock_llm.invoke.call_args
    # The prompt is the first positional argument
    return args[0]


# ---------------------------------------------------------------------------
# Test 1: Aggressive debator includes OPTIONS RISK ASSESSMENT when options active
# ---------------------------------------------------------------------------

def test_aggressive_options_block_present():
    """Aggressive debator prompt must contain 'OPTIONS RISK ASSESSMENT' when options_legs is non-empty."""
    from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator

    mock_llm = _make_mock_llm("Aggressive analyst response")
    state = _make_state()

    node = create_aggressive_debator(mock_llm)
    node(state)

    prompt = _get_invoked_prompt(mock_llm)
    assert "OPTIONS RISK ASSESSMENT" in prompt, (
        "Aggressive debator prompt must contain 'OPTIONS RISK ASSESSMENT' when options_legs is non-empty"
    )


# ---------------------------------------------------------------------------
# Test 2: Conservative debator includes OPTIONS RISK ASSESSMENT when options active
# ---------------------------------------------------------------------------

def test_conservative_options_block_present():
    """Conservative debator prompt must contain 'OPTIONS RISK ASSESSMENT' when options_legs is non-empty."""
    from tradingagents.agents.risk_mgmt.conservative_debator import create_conservative_debator

    mock_llm = _make_mock_llm("Conservative analyst response")
    state = _make_state()

    node = create_conservative_debator(mock_llm)
    node(state)

    prompt = _get_invoked_prompt(mock_llm)
    assert "OPTIONS RISK ASSESSMENT" in prompt, (
        "Conservative debator prompt must contain 'OPTIONS RISK ASSESSMENT' when options_legs is non-empty"
    )


# ---------------------------------------------------------------------------
# Test 3: Neutral debator includes OPTIONS RISK ASSESSMENT when options active
# ---------------------------------------------------------------------------

def test_neutral_options_block_present():
    """Neutral debator prompt must contain 'OPTIONS RISK ASSESSMENT' when options_legs is non-empty."""
    from tradingagents.agents.risk_mgmt.neutral_debator import create_neutral_debator

    mock_llm = _make_mock_llm("Neutral analyst response")
    state = _make_state()

    node = create_neutral_debator(mock_llm)
    node(state)

    prompt = _get_invoked_prompt(mock_llm)
    assert "OPTIONS RISK ASSESSMENT" in prompt, (
        "Neutral debator prompt must contain 'OPTIONS RISK ASSESSMENT' when options_legs is non-empty"
    )


# ---------------------------------------------------------------------------
# Test 4: Aggressive debator does NOT include OPTIONS RISK ASSESSMENT for equity-only
# ---------------------------------------------------------------------------

def test_aggressive_equity_only_no_options_block():
    """Aggressive debator prompt must NOT contain 'OPTIONS RISK ASSESSMENT' when options_legs is empty."""
    from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator

    mock_llm = _make_mock_llm("Aggressive analyst response")
    state = _make_equity_only_state()

    node = create_aggressive_debator(mock_llm)
    node(state)

    prompt = _get_invoked_prompt(mock_llm)
    assert "OPTIONS RISK ASSESSMENT" not in prompt, (
        "Aggressive debator prompt must NOT contain 'OPTIONS RISK ASSESSMENT' when options_legs is empty"
    )


# ---------------------------------------------------------------------------
# Test 5: Conservative debator does NOT include OPTIONS RISK ASSESSMENT for equity-only
# ---------------------------------------------------------------------------

def test_conservative_equity_only_no_options_block():
    """Conservative debator prompt must NOT contain 'OPTIONS RISK ASSESSMENT' when options_legs is empty."""
    from tradingagents.agents.risk_mgmt.conservative_debator import create_conservative_debator

    mock_llm = _make_mock_llm("Conservative analyst response")
    state = _make_equity_only_state()

    node = create_conservative_debator(mock_llm)
    node(state)

    prompt = _get_invoked_prompt(mock_llm)
    assert "OPTIONS RISK ASSESSMENT" not in prompt, (
        "Conservative debator prompt must NOT contain 'OPTIONS RISK ASSESSMENT' when options_legs is empty"
    )


# ---------------------------------------------------------------------------
# Test 6: Neutral debator does NOT include OPTIONS RISK ASSESSMENT for equity-only
# ---------------------------------------------------------------------------

def test_neutral_equity_only_no_options_block():
    """Neutral debator prompt must NOT contain 'OPTIONS RISK ASSESSMENT' when options_legs is empty."""
    from tradingagents.agents.risk_mgmt.neutral_debator import create_neutral_debator

    mock_llm = _make_mock_llm("Neutral analyst response")
    state = _make_equity_only_state()

    node = create_neutral_debator(mock_llm)
    node(state)

    prompt = _get_invoked_prompt(mock_llm)
    assert "OPTIONS RISK ASSESSMENT" not in prompt, (
        "Neutral debator prompt must NOT contain 'OPTIONS RISK ASSESSMENT' when options_legs is empty"
    )


# ---------------------------------------------------------------------------
# Test 7: Options block includes all required state field values
# ---------------------------------------------------------------------------

def test_options_block_includes_all_state_fields():
    """Options block must interpolate all six options state fields into the prompt."""
    from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator

    mock_llm = _make_mock_llm("Aggressive analyst response")
    state = _make_state()

    node = create_aggressive_debator(mock_llm)
    node(state)

    prompt = _get_invoked_prompt(mock_llm)

    # Each of these values must appear in the prompt
    assert state["options_strategy"] in prompt, (
        f"Prompt must contain options_strategy value '{state['options_strategy']}'"
    )
    assert state["options_legs"] in prompt, (
        f"Prompt must contain options_legs value"
    )
    assert state["options_pricing_report"] in prompt, (
        f"Prompt must contain options_pricing_report value '{state['options_pricing_report']}'"
    )
    assert state["greeks_report"] in prompt, (
        f"Prompt must contain greeks_report value '{state['greeks_report']}'"
    )
    assert state["volatility_report"] in prompt, (
        f"Prompt must contain volatility_report value '{state['volatility_report']}'"
    )
    assert state["options_flow_report"] in prompt, (
        f"Prompt must contain options_flow_report value '{state['options_flow_report']}'"
    )
