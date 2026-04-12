"""Tests for risk manager strategy context injection (D-02, D-23, D-24)."""
import pytest
from unittest.mock import MagicMock, patch


def _make_base_state(options_strategy="iron condor -- neutral", options_legs="LEG 1: SELL PUT AAPL 2026-05-10 $145.0"):
    """Create a minimal state dict for risk_manager_node."""
    return {
        "company_of_interest": "AAPL",
        "market_report": "Market is stable.",
        "technical_report": "Bullish trend.",
        "news_report": "No news.",
        "fundamentals_report": "Strong fundamentals.",
        "sentiment_report": "Positive sentiment.",
        "investment_plan": "Buy AAPL with iron condor.",
        "risk_debate_state": {
            "history": "Aggressive: buy. Conservative: hold. Neutral: cautious buy.",
            "aggressive_history": "Buy.",
            "conservative_history": "Hold.",
            "neutral_history": "Cautious buy.",
            "latest_speaker": "Neutral",
            "current_aggressive_response": "Buy.",
            "current_conservative_response": "Hold.",
            "current_neutral_response": "Cautious buy.",
            "count": 1,
        },
        "options_strategy": options_strategy,
        "options_legs": options_legs,
        "options_pricing_report": "Fair value.",
        "greeks_report": "Delta: 0.10, Theta: -0.05",
        "volatility_report": "IV Rank: 55.0",
        "options_flow_report": "Neutral flow.",
    }


def test_risk_manager_includes_strategy_context():
    """D-24: Risk manager prompt must include strategy metadata (margin_intensive, max_loss profile)."""
    from tradingagents.agents.managers.risk_manager import create_risk_manager

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="HOLD - risk too high")
    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_risk_manager(mock_llm, mock_memory)
    state = _make_base_state(options_strategy="iron condor -- neutral high IV")
    node(state)

    prompt_text = mock_llm.invoke.call_args[0][0]
    assert "margin_intensive" in prompt_text.lower() or "Margin Intensive" in prompt_text, (
        "Risk manager prompt must include margin_intensive context per D-24"
    )


def test_risk_manager_includes_stop_loss_rule():
    """D-02/D-23: Risk manager must include stop-loss enforcement rule for paper trading."""
    from tradingagents.agents.managers.risk_manager import create_risk_manager

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="BUY with caution")
    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_risk_manager(mock_llm, mock_memory)
    state = _make_base_state()
    node(state)

    prompt_text = mock_llm.invoke.call_args[0][0]
    assert "stop-loss" in prompt_text.lower() or "stop_loss" in prompt_text.lower(), (
        "Risk manager prompt must include stop-loss enforcement rule per D-02/D-23"
    )


def test_risk_manager_margin_intensive_flagged():
    """D-24: When strategy is margin_intensive, prompt should include margin warning."""
    from tradingagents.agents.managers.risk_manager import create_risk_manager

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="HOLD")
    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_risk_manager(mock_llm, mock_memory)
    # short_straddle is margin_intensive in the registry
    state = _make_base_state(options_strategy="short straddle -- high IV play")
    node(state)

    prompt_text = mock_llm.invoke.call_args[0][0]
    assert "margin" in prompt_text.lower(), (
        "Margin-intensive strategy must trigger margin warning in risk manager"
    )
