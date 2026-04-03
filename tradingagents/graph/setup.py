# TradingAgents/graph/setup.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.options import (
    create_volatility_analyst,
    create_options_flow_analyst,
    create_options_strategy_selector,
    create_strike_expiry_selector,
    create_options_pricing_agent,
    create_options_legs_builder,
    create_greeks_monitor,
)
from tradingagents.dataflows.config import get_config

from .conditional_logic import ConditionalLogic


# Options branch: sequential chain of 7 agents
# Note: LangGraph reserves ':' in node names — use dash separator instead.
OPTIONS_NODES = [
    ("Options - Volatility Analyst",  create_volatility_analyst),
    ("Options - Flow Analyst",        create_options_flow_analyst),
    ("Options - Strategy Selector",   create_options_strategy_selector),
    ("Options - Strike/Expiry",       create_strike_expiry_selector),
    ("Options - Pricing Agent",       create_options_pricing_agent),
    ("Options - Legs Builder",        create_options_legs_builder),
    ("Options - Greeks Monitor",      create_greeks_monitor),
]

# Maps factory function name -> state key it writes to
_OPTIONS_STATE_KEYS = {
    "create_volatility_analyst":       "volatility_report",
    "create_options_flow_analyst":     "options_flow_report",
    "create_options_strategy_selector": "options_strategy",
    "create_strike_expiry_selector":   "options_legs",
    "create_options_pricing_agent":    "options_pricing_report",
    "create_options_legs_builder":     "options_legs",
    "create_greeks_monitor":           "greeks_report",
}


def _safe_options_node(factory_fn, state_key, llm):
    """Wrap an options agent to catch errors and return empty string fallback."""
    inner = factory_fn(llm)

    def node(state: dict) -> dict:
        try:
            return inner(state)
        except Exception:
            return {state_key: ""}

    return node


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic

    def setup_graph(
        self, selected_analysts=["market", "technical", "social", "news", "fundamentals"]
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "technical": Technical analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in selected_analysts:
            analyst_nodes["market"] = create_market_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "technical" in selected_analysts:
            analyst_nodes["technical"] = create_technical_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["technical"] = create_msg_delete()
            # Technical analyst pre-fetches data — no tool-calling loop needed

        if "social" in selected_analysts:
            analyst_nodes["social"] = create_social_media_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["social"] = create_msg_delete()
            tool_nodes["social"] = self.tool_nodes["social"]

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]

        if "fundamentals" in selected_analysts:
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["fundamentals"] = create_msg_delete()
            tool_nodes["fundamentals"] = self.tool_nodes["fundamentals"]

        # Create researcher and manager nodes
        bull_researcher_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        research_manager_node = create_research_manager(
            self.deep_thinking_llm, self.invest_judge_memory
        )
        trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)

        # Create risk analysis nodes
        aggressive_analyst = create_aggressive_debator(self.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        conservative_analyst = create_conservative_debator(self.quick_thinking_llm)
        risk_manager_node = create_risk_manager(
            self.deep_thinking_llm, self.risk_manager_memory
        )

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            if analyst_type in tool_nodes:
                workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        # Add other nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Aggressive Analyst", aggressive_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Conservative Analyst", conservative_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

        # Define edges
        # Start with the first analyst
        first_analyst = selected_analysts[0]

        # Read enable_options from config
        cfg = get_config()
        enable_options = cfg.get("enable_options", False)

        first_equity = f"{first_analyst.capitalize()} Analyst"

        # Build list of all parallel branch entry points (equity analysts)
        equity_entries = [f"{a.capitalize()} Analyst" for a in selected_analysts]

        if enable_options:
            # Add all 7 options nodes with graceful error wrapping
            for node_name, factory_fn in OPTIONS_NODES:
                state_key = _OPTIONS_STATE_KEYS[factory_fn.__name__]
                workflow.add_node(
                    node_name,
                    _safe_options_node(factory_fn, state_key, self.quick_thinking_llm),
                )

            # Sequential chain within options branch
            for i in range(len(OPTIONS_NODES) - 1):
                workflow.add_edge(OPTIONS_NODES[i][0], OPTIONS_NODES[i + 1][0])

            # Fan-in: last options node -> Bull Researcher
            workflow.add_edge("Options - Greeks Monitor", "Bull Researcher")

            # Fan-out from START to all equity analysts + options branch in parallel
            all_branches = equity_entries + ["Options - Volatility Analyst"]

            def route_from_start(state):
                return all_branches

            workflow.add_conditional_edges(
                START,
                route_from_start,
                all_branches,
            )
        else:
            # Fan-out from START to all equity analysts in parallel
            def route_equity_start(state):
                return equity_entries

            workflow.add_conditional_edges(
                START,
                route_equity_start,
                equity_entries,
            )

        # Analysts that pre-fetch data and don't need tool-calling loops
        no_tool_analysts = {"technical"}

        # Connect each analyst's edges and fan-in to Bull Researcher
        for analyst_type in selected_analysts:
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            if analyst_type in no_tool_analysts:
                # Direct: analyst -> clear (no tool loop)
                workflow.add_edge(current_analyst, current_clear)
            else:
                # Tool-calling loop: analyst -> tools -> analyst -> clear
                current_tools = f"tools_{analyst_type}"
                workflow.add_conditional_edges(
                    current_analyst,
                    getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                    [current_tools, current_clear],
                )
                workflow.add_edge(current_tools, current_analyst)

            # All analysts fan-in to Bull Researcher
            workflow.add_edge(current_clear, "Bull Researcher")

        # Add remaining edges
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Aggressive Analyst")
        workflow.add_conditional_edges(
            "Aggressive Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Conservative Analyst": "Conservative Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Conservative Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Aggressive Analyst": "Aggressive Analyst",
                "Risk Judge": "Risk Judge",
            },
        )

        workflow.add_edge("Risk Judge", END)

        # Compile and return
        return workflow.compile()
