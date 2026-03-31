"""Tests for AgentState extension with options report fields."""
import pytest
from typing import get_type_hints


def test_agent_state_has_volatility_report_field():
    """AgentState must have a volatility_report field."""
    from tradingagents.agents.utils.agent_states import AgentState
    assert "volatility_report" in AgentState.__annotations__, (
        "AgentState missing 'volatility_report' field"
    )


def test_agent_state_has_options_flow_report_field():
    """AgentState must have an options_flow_report field."""
    from tradingagents.agents.utils.agent_states import AgentState
    assert "options_flow_report" in AgentState.__annotations__, (
        "AgentState missing 'options_flow_report' field"
    )


def test_agent_state_volatility_report_is_annotated_str():
    """volatility_report field annotation metadata should be a string description."""
    from tradingagents.agents.utils.agent_states import AgentState
    annotation = AgentState.__annotations__["volatility_report"]
    # Annotated[str, "description"] — check it's an Annotated type with str base
    import typing
    # Get the args of Annotated — first arg is the base type
    args = getattr(annotation, "__args__", None)
    assert args is not None, "volatility_report should be Annotated[str, ...]"
    assert args[0] is str, f"volatility_report base type should be str, got {args[0]}"


def test_agent_state_options_flow_report_is_annotated_str():
    """options_flow_report field annotation metadata should be a string description."""
    from tradingagents.agents.utils.agent_states import AgentState
    annotation = AgentState.__annotations__["options_flow_report"]
    args = getattr(annotation, "__args__", None)
    assert args is not None, "options_flow_report should be Annotated[str, ...]"
    assert args[0] is str, f"options_flow_report base type should be str, got {args[0]}"


def test_agent_state_has_options_strategy_field():
    """AgentState must have an options_strategy field."""
    from tradingagents.agents.utils.agent_states import AgentState
    assert "options_strategy" in AgentState.__annotations__, (
        "AgentState missing 'options_strategy' field"
    )


def test_agent_state_has_options_legs_field():
    """AgentState must have an options_legs field."""
    from tradingagents.agents.utils.agent_states import AgentState
    assert "options_legs" in AgentState.__annotations__, (
        "AgentState missing 'options_legs' field"
    )


def test_agent_state_options_strategy_is_annotated_str():
    """options_strategy field annotation base type should be str."""
    from tradingagents.agents.utils.agent_states import AgentState
    annotation = AgentState.__annotations__["options_strategy"]
    args = getattr(annotation, "__args__", None)
    assert args is not None, "options_strategy should be Annotated[str, ...]"
    assert args[0] is str, f"options_strategy base type should be str, got {args[0]}"


def test_agent_state_options_legs_is_annotated_str():
    """options_legs field annotation base type should be str."""
    from tradingagents.agents.utils.agent_states import AgentState
    annotation = AgentState.__annotations__["options_legs"]
    args = getattr(annotation, "__args__", None)
    assert args is not None, "options_legs should be Annotated[str, ...]"
    assert args[0] is str, f"options_legs base type should be str, got {args[0]}"


def test_create_volatility_analyst_importable_from_options_package():
    """create_volatility_analyst must be importable from tradingagents.agents.options."""
    from tradingagents.agents.options import create_volatility_analyst
    assert callable(create_volatility_analyst), (
        "create_volatility_analyst should be callable"
    )
