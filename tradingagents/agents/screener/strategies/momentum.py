"""Momentum & Volume screener strategy.

Refactored from the original screener_agent.py run_screener() logic.
Computes volume, momentum, and unusual activity signals, then uses
an LLM to rank candidates by conviction.
"""
from __future__ import annotations

from tradingagents.agents.screener.screener_agent import (
    ScreenerResult,
    create_screener_agent,
)
from tradingagents.agents.screener.registry import (
    ScreenerInfo,
    register_strategy,
)
from tradingagents.dataflows.screener_data import get_screener_signals


class MomentumStrategy:
    """Signal-based momentum and volume screening with LLM ranking."""

    def screen(self, config: dict, llm: object) -> ScreenerResult:
        candidates, _coverage = get_screener_signals(
            max_candidates=config.get("screener_max_candidates", 50)
        )

        # Unwrap BaseLLMClient wrappers to get the LangChain-compatible LLM
        if hasattr(llm, "get_llm"):
            llm = llm.get_llm()

        agent = create_screener_agent(llm)
        result = agent(candidates, config)

        if not isinstance(result, ScreenerResult):
            raise TypeError(f"Expected ScreenerResult, got {type(result)}")

        return result


# Auto-register on import
register_strategy(
    "momentum",
    ScreenerInfo(
        name="momentum",
        display_name="Momentum & Volume",
        description="Signal-based momentum and volume screening with LLM ranking. "
                    "Computes volume ratio, 5-day momentum, and unusual activity signals "
                    "across S&P 500, then uses an LLM to rank top candidates.",
    ),
    MomentumStrategy(),
)
