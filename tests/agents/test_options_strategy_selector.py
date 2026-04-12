"""Unit tests for create_options_strategy_selector factory.

All LLM calls are mocked. No live API calls are made in any test.
"""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm(content="bull call spread -- IV moderate, bias bullish"):
    """Create a mock LLM compatible with (prompt | llm).invoke({}) chain pattern."""
    mock_response = MagicMock()
    mock_response.content = content

    mock_llm = MagicMock()
    mock_llm.return_value = mock_response
    mock_llm.invoke = MagicMock(return_value=mock_response)

    return mock_llm, mock_response


def _make_state(
    volatility_report="IV Rank: 72 (high). IV Percentile: 80th.",
    options_flow_report="Net flow: bullish. Block trades detected.",
    investment_plan="Bullish — price target $160. Moderate confidence.",
):
    return {
        "company_of_interest": "AAPL",
        "trade_date": "2026-03-31",
        "messages": [],
        "volatility_report": volatility_report,
        "options_flow_report": options_flow_report,
        "investment_plan": investment_plan,
    }


# ---------------------------------------------------------------------------
# Test 1: Factory returns a callable
# ---------------------------------------------------------------------------

def test_factory_returns_callable():
    """create_options_strategy_selector(llm) must return a callable."""
    from tradingagents.agents.options.options_strategy_selector import (
        create_options_strategy_selector,
    )

    mock_llm, _ = _make_mock_llm()
    node = create_options_strategy_selector(mock_llm)
    assert callable(node), "Factory must return a callable node"


# ---------------------------------------------------------------------------
# Test 2: Node returns dict with options_strategy key
# ---------------------------------------------------------------------------

def test_node_returns_options_strategy():
    """Node must return a dict with 'options_strategy' key containing a string."""
    from tradingagents.agents.options.options_strategy_selector import (
        create_options_strategy_selector,
    )

    mock_llm, _ = _make_mock_llm("bull call spread -- IV moderate, bias bullish")
    node = create_options_strategy_selector(mock_llm)

    with patch("tradingagents.agents.options.options_strategy_selector.get_config",
               return_value={}):
        result = node(_make_state())

    assert isinstance(result, dict), "Node must return a dict"
    assert "options_strategy" in result, "Return dict must contain 'options_strategy' key"
    assert isinstance(result["options_strategy"], str), "options_strategy must be a string"


# ---------------------------------------------------------------------------
# Test 3: Output normalizes to a valid registry strategy key
# ---------------------------------------------------------------------------

def test_output_contains_valid_strategy_name():
    """When mock LLM returns 'bull call spread -- ...', normalized key is in registry."""
    from tradingagents.agents.options.options_strategy_selector import (
        create_options_strategy_selector,
    )
    from tradingagents.agents.options.strategies import REGISTRY, normalize_strategy_key

    mock_llm, _ = _make_mock_llm("bull call spread -- IV moderate, bias bullish")
    node = create_options_strategy_selector(mock_llm)

    with patch("tradingagents.agents.options.options_strategy_selector.get_config",
               return_value={}):
        result = node(_make_state())

    normalized = normalize_strategy_key(result["options_strategy"])
    assert normalized in REGISTRY.strategies, (
        f"Normalized key '{normalized}' not found in registry"
    )


# ---------------------------------------------------------------------------
# Test 4: No messages key in return dict
# ---------------------------------------------------------------------------

def test_no_messages_written():
    """Return dict must NOT contain 'messages' key."""
    from tradingagents.agents.options.options_strategy_selector import (
        create_options_strategy_selector,
    )

    mock_llm, _ = _make_mock_llm("iron condor -- IV high, neutral bias")
    node = create_options_strategy_selector(mock_llm)

    with patch("tradingagents.agents.options.options_strategy_selector.get_config",
               return_value={}):
        result = node(_make_state())

    assert "messages" not in result, (
        f"Return dict must NOT contain 'messages' key, got keys: {list(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 5: Empty reports do not crash
# ---------------------------------------------------------------------------

def test_empty_reports_no_crash():
    """Node runs without error when all upstream report fields are empty strings."""
    from tradingagents.agents.options.options_strategy_selector import (
        create_options_strategy_selector,
    )

    mock_llm, _ = _make_mock_llm("long call -- no context available")
    node = create_options_strategy_selector(mock_llm)

    state = _make_state(
        volatility_report="",
        options_flow_report="",
        investment_plan="",
    )

    with patch("tradingagents.agents.options.options_strategy_selector.get_config",
               return_value={}):
        # Must not raise
        result = node(state)

    assert "options_strategy" in result, "Must return options_strategy even with empty reports"


# ---------------------------------------------------------------------------
# Test 6: Registry has at least 30 strategies (replaces old STRATEGY_LIST==10 test)
# ---------------------------------------------------------------------------

def test_registry_has_at_least_30_strategies():
    """Registry must have at least 30 strategies (replacing old 10-strategy list)."""
    from tradingagents.agents.options.strategies import REGISTRY

    assert len(REGISTRY.strategies) >= 30, (
        f"Registry must have >= 30 strategies, got {len(REGISTRY.strategies)}"
    )


# ---------------------------------------------------------------------------
# Test 7: Factory importable from tradingagents.agents.options package
# ---------------------------------------------------------------------------

def test_importable_from_options_package():
    """create_options_strategy_selector must be importable from tradingagents.agents.options."""
    from tradingagents.agents.options import create_options_strategy_selector
    assert callable(create_options_strategy_selector)


# ---------------------------------------------------------------------------
# Test 8: Factory importable from tradingagents.agents
# ---------------------------------------------------------------------------

def test_importable_from_agents_package():
    """create_options_strategy_selector must be importable from tradingagents.agents."""
    from tradingagents.agents import create_options_strategy_selector
    assert callable(create_options_strategy_selector)
