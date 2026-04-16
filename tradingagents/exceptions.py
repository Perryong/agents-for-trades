"""Custom exception hierarchy for the trading agents framework.

All domain exceptions inherit from TradingAgentsError so callers can
catch the base class at pipeline boundaries while handling specific
errors where needed.
"""


class TradingAgentsError(Exception):
    """Base exception for all trading agent errors."""


class AgentProtocolError(TradingAgentsError):
    """Agent output failed schema validation.

    Attributes:
        ticker: The ticker symbol being analyzed (if available).
        agent_name: The name of the agent that produced invalid output.
    """

    def __init__(
        self,
        message: str,
        *,
        ticker: str | None = None,
        agent_name: str | None = None,
    ):
        super().__init__(message)
        self.ticker = ticker
        self.agent_name = agent_name


class StaleDataError(TradingAgentsError):
    """Data freshness check failed — data too old for consumption."""


class StaleRecommendationError(TradingAgentsError):
    """Recommendation past valid_until — cannot execute."""


class PipelineCheckpointError(TradingAgentsError):
    """Checkpoint save/restore failed."""


class ExecutionBackendError(TradingAgentsError):
    """Trade execution failed at the backend level."""


class MarketCalendarError(TradingAgentsError):
    """Market calendar query failed or returned unexpected state."""


class TokenBudgetExceededError(TradingAgentsError):
    """LLM token usage exceeded configured budget for this run."""
