"""Options strategy selector agent factory.

Reads volatility_report, options_flow_report, and investment_plan from state,
then uses a single LLM call to select one named options strategy from the
defined 10-strategy list.

Architecture: pure LLM agent — no Python metric computation. LLM selects
strategy based on directional bias, IV view, and time horizon embedded in
the upstream report text. Does NOT use bind_tools, MessagesPlaceholder,
or messages thread.
"""

from langchain_core.prompts import ChatPromptTemplate


# ---------------------------------------------------------------------------
# Strategy list (locked decision — do not alter names)
# ---------------------------------------------------------------------------

STRATEGY_LIST = [
    "long call",
    "long put",
    "bull call spread",
    "bear put spread",
    "iron condor",
    "covered call",
    "cash-secured put",
    "long straddle",
    "long strangle",
    "calendar spread",
]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a specialist options strategy selector. You will be given three "
    "analyst reports: a volatility report, an options flow report, and an "
    "investment plan. Your job is to select exactly one options strategy from "
    "the following list of ten strategies:\n\n"
    "1. long call\n"
    "2. long put\n"
    "3. bull call spread\n"
    "4. bear put spread\n"
    "5. iron condor\n"
    "6. covered call\n"
    "7. cash-secured put\n"
    "8. long straddle\n"
    "9. long strangle\n"
    "10. calendar spread\n\n"
    "You MUST pick exactly one strategy from this list. Do not invent or use "
    "any strategy name not on this list.\n\n"
    "Output format (exactly one line): "
    "<strategy name> -- <one-sentence rationale>\n\n"
    "Example: bull call spread -- IV is moderate and directional bias is bullish "
    "with defined downside risk preferred.\n\n"
    "Replace angle-bracket placeholders with actual values. "
    "Output one line only — no preamble, no postamble."
)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_options_strategy_selector(llm):
    """Factory that returns a LangGraph-compatible options strategy selector node.

    The returned node reads upstream report fields from state, then invokes
    the LLM once to select a single named strategy from STRATEGY_LIST.

    Returns:
        Callable: options_strategy_selector_node(state: dict) -> dict
            Return dict has exactly one key: "options_strategy".
            Does NOT write to state["messages"].
    """

    def options_strategy_selector_node(state: dict) -> dict:
        volatility_report: str = state.get("volatility_report", "")
        options_flow_report: str = state.get("options_flow_report", "")
        investment_plan: str = state.get("investment_plan", "")

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
            ("system", SYSTEM_PROMPT),
            ("human", data_content),
        ])

        result = (prompt | llm).invoke({})

        return {"options_strategy": result.content}

    return options_strategy_selector_node
