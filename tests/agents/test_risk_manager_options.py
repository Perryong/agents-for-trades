"""Unit tests for options-aware Risk Manager.

Tests verify:
  - OPTIONS RISK RULES block is included in prompt when options_legs is non-empty
  - OPTIONS RISK RULES block is NOT included when options_legs is empty (equity-only)
  - All 5 rule names are present in the options rules block
  - Options state fields are interpolated into the prompt
  - Return dict contains final_trade_decision key (unchanged behaviour)

No live LLM or API calls are made.
"""
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm(content="Buy. Risk assessment complete."):
    """Return a MagicMock LLM where mock_llm.invoke(...).content == content."""
    mock_response = MagicMock()
    mock_response.content = content

    mock_llm = MagicMock()
    mock_llm.invoke = MagicMock(return_value=mock_response)
    mock_llm.return_value = mock_response

    return mock_llm


def _make_state(options_legs="LEG 1: BUY CALL AAPL 2026-05-10 $150 delta=0.30 OI=300 [PASS]"):
    """Return a state dict for the risk manager node."""
    return {
        "company_of_interest": "AAPL",
        "market_report": "market data",
        "sentiment_report": "sentiment data",
        "news_report": "news data",
        "fundamentals_report": "fundamentals data",
        "investment_plan": "Buy AAPL stock",
        "trader_investment_plan": "Buy AAPL",
        "technical_report": "RSI at 55, neutral",
        "risk_debate_state": {
            "history": "Aggressive: buy. Conservative: cautious. Neutral: balanced.",
            "aggressive_history": "Aggressive: buy.",
            "conservative_history": "Conservative: cautious.",
            "neutral_history": "Neutral: balanced.",
            "current_aggressive_response": "buy aggressively",
            "current_conservative_response": "be cautious",
            "current_neutral_response": "balanced approach",
            "count": 3,
        },
        "options_strategy": "long call",
        "options_legs": options_legs,
        "options_pricing_report": "Edge: +5%, Verdict: positive edge",
        "greeks_report": "Net delta: $2000, Net theta: -$50/day, Flags: none",
        "volatility_report": "IV rank 45",
        "options_flow_report": "Normal flow",
    }


def _make_equity_state():
    """Return an equity-only state with all options fields as empty strings."""
    state = _make_state(options_legs="")
    state["options_strategy"] = ""
    state["options_pricing_report"] = ""
    state["greeks_report"] = ""
    state["volatility_report"] = ""
    state["options_flow_report"] = ""
    return state


def _capture_prompt(mock_llm, mock_memory, state):
    """Call create_risk_manager with given state, return the prompt string passed to llm.invoke."""
    from tradingagents.agents.managers.risk_manager import create_risk_manager

    mock_memory.get_memories.return_value = []

    node = create_risk_manager(mock_llm, mock_memory)
    node(state)

    # The prompt is the first positional argument to llm.invoke
    call_args = mock_llm.invoke.call_args
    prompt = call_args[0][0]  # positional arg 0
    return prompt


# ---------------------------------------------------------------------------
# Test 1: OPTIONS RISK RULES present when options_legs is non-empty
# ---------------------------------------------------------------------------

def test_risk_manager_options_rules_present():
    """Prompt must contain 'OPTIONS RISK RULES' when state has non-empty options_legs."""
    mock_llm = _make_mock_llm()
    mock_memory = MagicMock()

    state = _make_state()
    prompt = _capture_prompt(mock_llm, mock_memory, state)

    assert "OPTIONS RISK RULES" in prompt, (
        "Prompt must contain 'OPTIONS RISK RULES' when options_legs is non-empty"
    )


# ---------------------------------------------------------------------------
# Test 2: OPTIONS RISK RULES absent for equity-only state
# ---------------------------------------------------------------------------

def test_risk_manager_equity_only_no_options_rules():
    """Prompt must NOT contain 'OPTIONS RISK RULES' when options_legs is empty string."""
    mock_llm = _make_mock_llm()
    mock_memory = MagicMock()

    state = _make_equity_state()
    prompt = _capture_prompt(mock_llm, mock_memory, state)

    assert "OPTIONS RISK RULES" not in prompt, (
        "Prompt must NOT contain 'OPTIONS RISK RULES' in equity-only mode (options_legs='')"
    )


# ---------------------------------------------------------------------------
# Test 3: All 5 rule names present in options prompt
# ---------------------------------------------------------------------------

def test_risk_manager_all_five_rules_named():
    """Prompt must contain all 5 options rule names when options_legs is non-empty."""
    mock_llm = _make_mock_llm()
    mock_memory = MagicMock()

    state = _make_state()
    prompt = _capture_prompt(mock_llm, mock_memory, state)

    for rule_name in ["Max Loss Gate", "Exit Rule", "Early Assignment", "Greeks Threshold", "Negative Theta"]:
        assert rule_name in prompt, (
            f"Prompt must contain rule name '{rule_name}' when options_legs is non-empty"
        )


# ---------------------------------------------------------------------------
# Test 4: Options state fields are interpolated into the prompt
# ---------------------------------------------------------------------------

def test_risk_manager_options_state_fields_interpolated():
    """Prompt must contain interpolated values from options state fields."""
    mock_llm = _make_mock_llm()
    mock_memory = MagicMock()

    state = _make_state()
    prompt = _capture_prompt(mock_llm, mock_memory, state)

    assert "long call" in prompt, "Prompt must contain interpolated options_strategy value"
    assert "LEG 1: BUY CALL AAPL 2026-05-10 $150 delta=0.30 OI=300 [PASS]" in prompt, (
        "Prompt must contain interpolated options_legs value"
    )
    assert "Edge: +5%" in prompt, "Prompt must contain interpolated options_pricing_report value"
    assert "Net delta: $2000" in prompt, "Prompt must contain interpolated greeks_report value"


# ---------------------------------------------------------------------------
# Test 5: Return dict contains final_trade_decision key
# ---------------------------------------------------------------------------

def test_risk_manager_returns_final_trade_decision():
    """Risk manager must return a dict containing 'final_trade_decision' key."""
    mock_llm = _make_mock_llm("Buy. Risk assessment complete.")
    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    from tradingagents.agents.managers.risk_manager import create_risk_manager

    state = _make_state()
    node = create_risk_manager(mock_llm, mock_memory)
    result = node(state)

    assert isinstance(result, dict), "Risk manager must return a dict"
    assert "final_trade_decision" in result, (
        "Return dict must contain 'final_trade_decision' key"
    )
