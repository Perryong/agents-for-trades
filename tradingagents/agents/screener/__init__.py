"""Screener agent subpackage.

Re-exports the public API for the LLM screener module.
Auto-registers all strategies on import.
"""

from .screener_agent import create_screener_agent, run_screener, TopPick, ScreenerResult
from .registry import get_strategy, list_strategies, register_strategy, ScreenerStrategy, ScreenerInfo

# Auto-register built-in strategies
from . import strategies  # noqa: F401

__all__ = [
    "create_screener_agent", "run_screener", "TopPick", "ScreenerResult",
    "get_strategy", "list_strategies", "register_strategy",
    "ScreenerStrategy", "ScreenerInfo",
]
