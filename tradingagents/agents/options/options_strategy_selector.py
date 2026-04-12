"""Options strategy selector agent factory.

Reads volatility_report, options_flow_report, and investment_plan from state,
builds a GateContext from those reports, calls filter_strategies to produce a
3-6 strategy shortlist, then uses a single LLM call to select one strategy.

Architecture: gate-filtered LLM agent — Python narrows the candidate set via
hard eligibility gates + soft scoring; LLM makes the final selection from the
shortlist. Does NOT use bind_tools, MessagesPlaceholder, or messages thread.
"""

import re

from langchain_core.prompts import ChatPromptTemplate

from tradingagents.agents.options.strategies import (
    REGISTRY,
    GateContext,
    filter_strategies,
    normalize_strategy_key,
)
from tradingagents.dataflows.config import get_config


# ---------------------------------------------------------------------------
# Gate context extraction
# ---------------------------------------------------------------------------


def _extract_gate_context(state: dict, config: dict) -> GateContext:
    """Build a GateContext from state report strings and runtime config.

    Extracts signals from upstream text reports (volatility_report,
    investment_plan, options_flow_report) using simple regex / keyword
    matching so that no LLM call is needed for signal extraction.

    Args:
        state:  LangGraph AgentState dict.
        config: Current runtime config dict from get_config().

    Returns:
        Populated GateContext ready to pass to filter_strategies().
    """
    volatility_report: str = state.get("volatility_report", "") or ""
    investment_plan: str = state.get("investment_plan", "") or ""
    options_flow_report: str = state.get("options_flow_report", "") or ""

    # ------------------------------------------------------------------
    # IV Rank — parse from volatility report
    # ------------------------------------------------------------------
    iv_rank: float = 50.0
    match = re.search(r"IV\s*Rank[:\s]*([0-9]+(?:\.[0-9]+)?)", volatility_report, re.IGNORECASE)
    if match:
        try:
            iv_rank = float(match.group(1))
        except ValueError:
            iv_rank = 50.0

    # ------------------------------------------------------------------
    # IV environment
    # ------------------------------------------------------------------
    if iv_rank < 30:
        iv_env = "low"
    elif iv_rank > 60:
        iv_env = "high"
    else:
        iv_env = "any"

    # ------------------------------------------------------------------
    # Directional bias — keyword scan of investment_plan
    # ------------------------------------------------------------------
    plan_lower = investment_plan.lower()
    bullish_keywords = {"bullish", "long", "buy", "upside", "calls"}
    bearish_keywords = {"bearish", "short", "sell", "downside", "puts"}

    bias: str = "neutral"
    plan_words = set(plan_lower.split())
    if plan_words & bullish_keywords:
        bias = "bullish"
    elif plan_words & bearish_keywords:
        bias = "bearish"

    # ------------------------------------------------------------------
    # Multi-expiry availability — check for bucket / DTE markers
    # ------------------------------------------------------------------
    has_multi_expiry: bool = bool(
        re.search(r"Bucket|DTE", options_flow_report, re.IGNORECASE)
    ) if options_flow_report else True

    # ------------------------------------------------------------------
    # Margin / liquidity settings from config
    # ------------------------------------------------------------------
    available_margin: float | None = config.get("available_margin", None)
    exclude_margin_intensive: bool = config.get("exclude_margin_intensive", False)
    min_oi_threshold: int = int(config.get("options_min_oi", 100))

    # ------------------------------------------------------------------
    # DTE / expiry proximity
    # ------------------------------------------------------------------
    near_dte: int = int(config.get("near_dte", 30))

    # ------------------------------------------------------------------
    # Earnings proximity heuristic (D-14)
    # ------------------------------------------------------------------
    iv_rank_for_earnings: float = iv_rank
    is_earnings_proximity: bool = (
        (near_dte <= 7 and iv_rank >= 75) or
        (near_dte <= 14 and iv_rank >= 90)
    )

    return GateContext(
        bias=bias,
        iv_rank=iv_rank,
        iv_env=iv_env,
        has_multi_expiry=has_multi_expiry,
        available_margin=available_margin,
        exclude_margin_intensive=exclude_margin_intensive,
        min_oi_threshold=min_oi_threshold,
        near_dte=near_dte,
        iv_rank_for_earnings=iv_rank_for_earnings,
        is_earnings_proximity=is_earnings_proximity,
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_options_strategy_selector(llm):
    """Factory that returns a LangGraph-compatible options strategy selector node.

    The returned node:
    1. Builds a GateContext from upstream report fields.
    2. Calls filter_strategies to produce a 3-6 strategy shortlist.
    3. Invokes the LLM once to pick the best strategy from the shortlist.
    4. Returns the raw LLM output in "options_strategy" for downstream display.

    Returns:
        Callable: options_strategy_selector_node(state: dict) -> dict
            Return dict has exactly one key: "options_strategy".
            Does NOT write to state["messages"].
    """

    def options_strategy_selector_node(state: dict) -> dict:
        config = get_config()
        context = _extract_gate_context(state, config)
        shortlist = filter_strategies(REGISTRY, context)

        # Build dynamic strategy list for the prompt
        strategy_list_text = "\n".join(
            f"{i + 1}. {name.replace('_', ' ')}" for i, name in enumerate(shortlist)
        )

        system_prompt = (
            "You are a specialist options strategy selector. You will be given three "
            "analyst reports: a volatility report, an options flow report, and an "
            "investment plan. Your job is to select exactly one strategy from the "
            f"following list of {len(shortlist)} strategies:\n\n"
            f"{strategy_list_text}\n\n"
            "You MUST pick exactly one strategy from this list. Do not invent or use "
            "any strategy name not on this list.\n\n"
            "Output format (exactly one line): "
            "<strategy name> -- <one-sentence rationale>\n\n"
            "Example: bull call spread -- IV is moderate and directional bias is bullish "
            "with defined downside risk preferred.\n\n"
            "Replace angle-bracket placeholders with actual values. "
            "Output one line only — no preamble, no postamble."
        )

        volatility_report: str = state.get("volatility_report", "") or ""
        options_flow_report: str = state.get("options_flow_report", "") or ""
        investment_plan: str = state.get("investment_plan", "") or ""

        data_content = (
            "VOLATILITY REPORT:\n"
            f"{volatility_report if volatility_report else 'No volatility report available.'}\n\n"
            "OPTIONS FLOW REPORT:\n"
            f"{options_flow_report if options_flow_report else 'No options flow report available.'}\n\n"
            "INVESTMENT PLAN:\n"
            f"{investment_plan if investment_plan else 'No investment plan available.'}\n\n"
            "Based on the above, select exactly one options strategy from the list."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", data_content),
        ])

        result = (prompt | llm).invoke({})

        # Normalize for downstream use (normalization result is informational;
        # raw LLM output is kept in state for display)
        normalize_strategy_key(result.content)  # validates / logs intent

        return {"options_strategy": result.content}

    return options_strategy_selector_node
