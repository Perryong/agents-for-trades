"""Tests for tradingagents.exceptions — custom exception hierarchy."""

import pytest
from tradingagents.exceptions import (
    TradingAgentsError,
    AgentProtocolError,
    StaleDataError,
    StaleRecommendationError,
    PipelineCheckpointError,
    ExecutionBackendError,
    MarketCalendarError,
    TokenBudgetExceededError,
)


class TestExceptionHierarchy:
    """All custom exceptions inherit from TradingAgentsError."""

    @pytest.mark.parametrize(
        "exc_class",
        [
            AgentProtocolError,
            StaleDataError,
            StaleRecommendationError,
            PipelineCheckpointError,
            ExecutionBackendError,
            MarketCalendarError,
            TokenBudgetExceededError,
        ],
    )
    def test_subclass_of_trading_agents_error(self, exc_class):
        assert issubclass(exc_class, TradingAgentsError)

    @pytest.mark.parametrize(
        "exc_class",
        [
            TradingAgentsError,
            AgentProtocolError,
            StaleDataError,
            StaleRecommendationError,
            PipelineCheckpointError,
            ExecutionBackendError,
            MarketCalendarError,
            TokenBudgetExceededError,
        ],
    )
    def test_subclass_of_exception(self, exc_class):
        assert issubclass(exc_class, Exception)

    def test_catch_all_with_base(self):
        """Catching TradingAgentsError catches all custom exceptions."""
        for exc_class in [
            AgentProtocolError,
            StaleDataError,
            StaleRecommendationError,
            PipelineCheckpointError,
            ExecutionBackendError,
            MarketCalendarError,
            TokenBudgetExceededError,
        ]:
            with pytest.raises(TradingAgentsError):
                raise exc_class("test")


class TestExceptionMessages:
    """All exceptions accept descriptive messages."""

    def test_trading_agents_error_message(self):
        exc = TradingAgentsError("base error")
        assert str(exc) == "base error"

    def test_agent_protocol_error_message(self):
        exc = AgentProtocolError("invalid output")
        assert str(exc) == "invalid output"

    def test_stale_data_error_message(self):
        exc = StaleDataError("data too old")
        assert str(exc) == "data too old"


class TestAgentProtocolErrorContext:
    """AgentProtocolError accepts optional ticker and agent_name kwargs."""

    def test_with_ticker_and_agent_name(self):
        exc = AgentProtocolError(
            "invalid output", ticker="AAPL", agent_name="fundamentals"
        )
        assert exc.ticker == "AAPL"
        assert exc.agent_name == "fundamentals"
        assert "invalid output" in str(exc)

    def test_without_optional_kwargs(self):
        exc = AgentProtocolError("invalid output")
        assert exc.ticker is None
        assert exc.agent_name is None

    def test_with_only_ticker(self):
        exc = AgentProtocolError("bad data", ticker="NVDA")
        assert exc.ticker == "NVDA"
        assert exc.agent_name is None
