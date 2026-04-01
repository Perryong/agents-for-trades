"""Integration tests for graph wiring — options branch in StateGraph.

All LLM and data-layer calls are mocked. No live API calls are made.

RED phase: These tests fail until setup.py, propagation.py, and trading_graph.py
           are updated to wire the options branch.
"""
from unittest.mock import patch, MagicMock
import pytest
import pandas as pd
from langchain_core.messages import AIMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm():
    """Create a mock LLM compatible with LangChain RunnableSequence."""
    mock_response = MagicMock()
    mock_response.content = "mock report"
    mock_llm = MagicMock()
    mock_llm.return_value = mock_response
    mock_llm.invoke = MagicMock(return_value=mock_response)
    return mock_llm


def _make_graph_setup(enable_options=False):
    """Build a GraphSetup with all mocked dependencies.

    Patches get_config to return a config with the given enable_options flag.
    Returns the compiled graph.
    """
    from tradingagents.graph.setup import GraphSetup
    from tradingagents.graph.conditional_logic import ConditionalLogic

    mock_llm = _make_mock_llm()
    mock_memory = MagicMock()

    # Minimal tool nodes — ToolNode expects a list of tools
    from langchain_core.tools import tool as lc_tool

    @lc_tool
    def _dummy_tool(query: str) -> str:
        """Dummy tool for testing."""
        return "dummy"

    from langgraph.prebuilt import ToolNode
    dummy_tool_node = ToolNode([_dummy_tool])

    tool_nodes = {
        "market": dummy_tool_node,
        "technical": dummy_tool_node,
        "social": dummy_tool_node,
        "news": dummy_tool_node,
        "fundamentals": dummy_tool_node,
    }

    conditional_logic = ConditionalLogic(
        max_debate_rounds=1,
        max_risk_discuss_rounds=1,
    )

    graph_setup = GraphSetup(
        quick_thinking_llm=mock_llm,
        deep_thinking_llm=mock_llm,
        tool_nodes=tool_nodes,
        bull_memory=mock_memory,
        bear_memory=mock_memory,
        trader_memory=mock_memory,
        invest_judge_memory=mock_memory,
        risk_manager_memory=mock_memory,
        conditional_logic=conditional_logic,
    )

    config_dict = {
        "enable_options": enable_options,
        "options_vendor": "tradier",
        "options_delta_target": 0.30,
        "options_dte_window": [21, 45],
        "options_min_oi": 100,
    }

    with patch("tradingagents.graph.setup.get_config", return_value=config_dict):
        compiled = graph_setup.setup_graph(
            selected_analysts=["market", "technical", "social", "news", "fundamentals"]
        )

    return compiled


# ---------------------------------------------------------------------------
# Test: initial state has options fields
# ---------------------------------------------------------------------------

def test_initial_state_has_options_fields():
    """Propagator.create_initial_state must include all 6 options fields with '' defaults."""
    from tradingagents.graph.propagation import Propagator

    state = Propagator().create_initial_state("AAPL", "2025-01-15")

    options_keys = [
        "volatility_report",
        "options_flow_report",
        "options_strategy",
        "options_legs",
        "options_pricing_report",
        "greeks_report",
    ]
    for key in options_keys:
        assert key in state, f"Missing options field: {key}"
        assert state[key] == "", f"Expected empty string default for {key}, got: {state[key]!r}"


# ---------------------------------------------------------------------------
# Test: equity-only mode — no Options: nodes in compiled graph
# ---------------------------------------------------------------------------

def test_setup_graph_equity_only_no_options_nodes():
    """When enable_options=False, compiled graph must NOT contain any 'Options' nodes."""
    compiled = _make_graph_setup(enable_options=False)
    node_names = list(compiled.get_graph().nodes.keys())
    options_nodes = [n for n in node_names if n.startswith("Options")]
    assert options_nodes == [], (
        f"Equity-only graph should have no 'Options' nodes, found: {options_nodes}"
    )


# ---------------------------------------------------------------------------
# Test: options-enabled mode — all 7 Options: nodes present
# ---------------------------------------------------------------------------

def test_setup_graph_options_enabled_has_options_nodes():
    """When enable_options=True, compiled graph must contain all 7 'Options:' nodes."""
    compiled = _make_graph_setup(enable_options=True)
    node_names = list(compiled.get_graph().nodes.keys())

    expected_options_nodes = [
        "Options - Volatility Analyst",
        "Options - Flow Analyst",
        "Options - Strategy Selector",
        "Options - Strike/Expiry",
        "Options - Pricing Agent",
        "Options - Legs Builder",
        "Options - Greeks Monitor",
    ]
    for node in expected_options_nodes:
        assert node in node_names, (
            f"Expected options node '{node}' not found. Available nodes: {node_names}"
        )


# ---------------------------------------------------------------------------
# Test: Options: Greeks Monitor fans in to Bull Researcher
# ---------------------------------------------------------------------------

def test_setup_graph_options_fan_in_to_bull_researcher():
    """When enable_options=True, 'Options: Greeks Monitor' must have an edge to 'Bull Researcher'."""
    compiled = _make_graph_setup(enable_options=True)
    graph_repr = compiled.get_graph()

    # Collect all edges from the graph
    edges = [(e.source, e.target) for e in graph_repr.edges]
    fan_in_edge = ("Options - Greeks Monitor", "Bull Researcher")
    assert fan_in_edge in edges, (
        f"Expected edge {fan_in_edge} not found. Edges: {edges}"
    )


# ---------------------------------------------------------------------------
# Test: _log_state includes options fields
# ---------------------------------------------------------------------------

def test_log_state_includes_options_fields():
    """TradingAgentsGraph._log_state must include all 6 options fields in logged dict."""
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    # Build a minimal final_state dict — all required fields including options
    final_state = {
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "market_report": "market",
        "technical_report": "technical",
        "sentiment_report": "sentiment",
        "news_report": "news",
        "fundamentals_report": "fundamentals",
        "investment_debate_state": {
            "bull_history": "",
            "bear_history": "",
            "history": "",
            "current_response": "",
            "judge_decision": "",
        },
        "trader_investment_plan": "buy",
        "risk_debate_state": {
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "history": "",
            "judge_decision": "",
        },
        "investment_plan": "buy AAPL",
        "final_trade_decision": "BUY",
        # Options fields
        "volatility_report": "vol report",
        "options_flow_report": "flow report",
        "options_strategy": "bull call spread",
        "options_legs": "leg1",
        "options_pricing_report": "pricing report",
        "greeks_report": "greeks report",
    }

    # Instantiate TradingAgentsGraph with mocked LLM/deps to avoid real connections
    with patch("tradingagents.graph.trading_graph.create_llm_client") as mock_client_factory, \
         patch("tradingagents.graph.trading_graph.FinancialSituationMemory") as mock_mem_cls, \
         patch("tradingagents.graph.trading_graph.GraphSetup") as mock_gs_cls, \
         patch("tradingagents.graph.trading_graph.Propagator"), \
         patch("tradingagents.graph.trading_graph.Reflector"), \
         patch("tradingagents.graph.trading_graph.SignalProcessor"), \
         patch("tradingagents.graph.trading_graph.set_config"), \
         patch("os.makedirs"):

        mock_llm_instance = _make_mock_llm()
        mock_client = MagicMock()
        mock_client.get_llm.return_value = mock_llm_instance
        mock_client_factory.return_value = mock_client

        mock_mem_cls.return_value = MagicMock()
        mock_gs = MagicMock()
        mock_gs.setup_graph.return_value = MagicMock()
        mock_gs_cls.return_value = mock_gs

        tag = TradingAgentsGraph.__new__(TradingAgentsGraph)
        tag.log_states_dict = {}
        tag.ticker = "AAPL"
        tag.config = {"project_dir": "/tmp"}

        # Patch file writing to avoid actual disk writes
        with patch("builtins.open", MagicMock()), \
             patch("tradingagents.graph.trading_graph.Path") as mock_path:
            mock_path.return_value.mkdir = MagicMock()
            tag._log_state("2025-01-15", final_state)

    logged = tag.log_states_dict["2025-01-15"]

    options_fields = [
        "volatility_report",
        "options_flow_report",
        "options_strategy",
        "options_legs",
        "options_pricing_report",
        "greeks_report",
    ]
    for field in options_fields:
        assert field in logged, f"Missing options field '{field}' in _log_state output"
        assert logged[field] == final_state[field], (
            f"Field '{field}': expected {final_state[field]!r}, got {logged[field]!r}"
        )


# ---------------------------------------------------------------------------
# Smoke test helpers
# ---------------------------------------------------------------------------

def _make_proper_mock_llm():
    """Create a mock LLM that works with LangChain bind_tools and RunnableSequence.

    Key requirements:
    - bind_tools() must return the same mock (so .invoke() is configured)
    - .invoke() and __call__ must return an AIMessage with tool_calls=[]
      so conditional_logic sees no tool calls and routes to Msg Clear node
    """
    ai_msg = AIMessage(content="mock report", tool_calls=[])
    mock_llm = MagicMock()
    mock_llm.return_value = ai_msg        # __call__ path (RunnableSequence)
    mock_llm.invoke.return_value = ai_msg  # .invoke() path
    mock_llm.bind_tools.return_value = mock_llm  # bind_tools returns same mock
    return mock_llm


def _make_smoke_graph(enable_options: bool):
    """Build a compiled graph with a single 'market' analyst and all deps mocked.

    Uses GraphSetup directly (avoids TradingAgentsGraph.__init__ complexity).
    Returns the compiled graph and graph args.
    """
    from tradingagents.graph.setup import GraphSetup
    from tradingagents.graph.conditional_logic import ConditionalLogic
    from tradingagents.graph.propagation import Propagator
    from langchain_core.tools import tool as lc_tool
    from langgraph.prebuilt import ToolNode

    mock_llm = _make_proper_mock_llm()

    @lc_tool
    def _dummy_tool(query: str) -> str:
        """Dummy tool for graph smoke tests."""
        return "dummy"

    dummy_tool_node = ToolNode([_dummy_tool])
    tool_nodes = {"market": dummy_tool_node}

    conditional_logic = ConditionalLogic(
        max_debate_rounds=1,
        max_risk_discuss_rounds=1,
    )

    graph_setup = GraphSetup(
        quick_thinking_llm=mock_llm,
        deep_thinking_llm=mock_llm,
        tool_nodes=tool_nodes,
        bull_memory=MagicMock(),
        bear_memory=MagicMock(),
        trader_memory=MagicMock(),
        invest_judge_memory=MagicMock(),
        risk_manager_memory=MagicMock(),
        conditional_logic=conditional_logic,
    )

    config_dict = {
        "enable_options": enable_options,
        "options_vendor": "tradier",
        "options_delta_target": 0.30,
        "options_dte_window": [21, 45],
        "options_min_oi": 100,
    }

    with patch("tradingagents.graph.setup.get_config", return_value=config_dict):
        compiled = graph_setup.setup_graph(selected_analysts=["market"])

    propagator = Propagator()
    init_state = propagator.create_initial_state("AAPL", "2025-01-15")
    args = propagator.get_graph_args()

    return compiled, init_state, args


def _make_options_data_patches():
    """Return a dict of mock route_to_vendor side_effect and yfinance mock."""
    prices = pd.Series([150.0 + i * 0.1 for i in range(90)])
    mock_hist = pd.DataFrame({"Close": prices})
    mock_yf = MagicMock()
    mock_yf.Ticker.return_value.history.return_value = mock_hist

    valid_iv_str = (
        "date    iv\n"
        "2025-04-01  0.20\n"
        "2025-07-01  0.25\n"
        "2026-01-01  0.35\n"
        "2026-04-01  0.40\n"
    )
    chain_str = (
        "strike  option_type  volume  open_interest  iv  delta\n"
        "145.0  call  1000  500  0.28  0.55\n"
        "150.0  put  900  450  0.32  -0.45\n"
    )

    def mock_route(method, *args, **kwargs):
        if method == "get_historical_iv":
            return valid_iv_str
        if method == "get_options_expirations":
            return ["2026-04-17", "2026-06-20"]
        if method == "get_options_chain":
            return chain_str
        return ""

    return mock_route, mock_yf


# ---------------------------------------------------------------------------
# Smoke Test 1: options enabled → all 6 options fields populated
# ---------------------------------------------------------------------------

def test_full_graph_options_enabled_populates_all_fields():
    """Full graph run with enable_options=True must populate all 6 options state fields."""
    compiled, init_state, args = _make_smoke_graph(enable_options=True)
    mock_route, mock_yf = _make_options_data_patches()

    with patch("tradingagents.dataflows.interface.route_to_vendor", side_effect=mock_route), \
         patch("tradingagents.agents.options.volatility_analyst.route_to_vendor", side_effect=mock_route), \
         patch("tradingagents.agents.options.options_flow_analyst.route_to_vendor", side_effect=mock_route), \
         patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
        final_state = compiled.invoke(init_state, **args)

    # All 6 options fields must be non-empty strings
    assert final_state["volatility_report"] != "", "volatility_report must be non-empty"
    assert final_state["options_flow_report"] != "", "options_flow_report must be non-empty"
    assert final_state["options_strategy"] != "", "options_strategy must be non-empty"
    assert final_state["options_legs"] != "", "options_legs must be non-empty"
    assert final_state["options_pricing_report"] != "", "options_pricing_report must be non-empty"
    assert final_state["greeks_report"] != "", "greeks_report must be non-empty"

    # Equity pipeline must also work
    assert final_state["market_report"] != "", "market_report must be non-empty (equity still works)"


# ---------------------------------------------------------------------------
# Smoke Test 2: equity-only mode → options fields empty, equity populated
# ---------------------------------------------------------------------------

def test_full_graph_equity_only_no_options_content():
    """Full graph run with "enable_options": False must leave options fields as empty strings."""
    compiled, init_state, args = _make_smoke_graph(enable_options=False)
    mock_route, mock_yf = _make_options_data_patches()

    # equity-only mode — no options data patches needed, but use them anyway to be safe
    with patch("tradingagents.dataflows.interface.route_to_vendor", side_effect=mock_route), \
         patch("tradingagents.agents.options.volatility_analyst.route_to_vendor", side_effect=mock_route), \
         patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
        final_state = compiled.invoke(init_state, **args)

    # Options fields must remain empty (no options branch was run)
    assert final_state["volatility_report"] == "", (
        f"volatility_report must be empty in equity-only mode, got: {final_state['volatility_report']!r}"
    )
    assert final_state["options_flow_report"] == "", (
        f"options_flow_report must be empty in equity-only mode"
    )
    assert final_state["options_strategy"] == "", (
        f"options_strategy must be empty in equity-only mode"
    )
    assert final_state["options_legs"] == "", (
        f"options_legs must be empty in equity-only mode"
    )
    assert final_state["options_pricing_report"] == "", (
        f"options_pricing_report must be empty in equity-only mode"
    )
    assert final_state["greeks_report"] == "", (
        f"greeks_report must be empty in equity-only mode"
    )

    # Equity pipeline must still work
    assert final_state["market_report"] != "", "market_report must be non-empty in equity-only mode"


# ---------------------------------------------------------------------------
# Smoke Test 3: graceful degradation — one options agent failure
# ---------------------------------------------------------------------------

def test_options_branch_failure_graceful_degradation():
    """When one options agent raises, the graph completes; that agent's field is empty."""
    from tradingagents.graph.setup import OPTIONS_NODES

    mock_route, mock_yf = _make_options_data_patches()

    # Build a patched OPTIONS_NODES where the flow analyst raises RuntimeError
    def failing_flow_factory(llm):
        def node(state):
            raise RuntimeError("data unavailable")
        return node

    # __name__ must match the _OPTIONS_STATE_KEYS lookup
    failing_flow_factory.__name__ = "create_options_flow_analyst"

    patched_nodes = [
        (name, failing_flow_factory if name == "Options - Flow Analyst" else fn)
        for name, fn in OPTIONS_NODES
    ]

    from tradingagents.graph.setup import GraphSetup
    from tradingagents.graph.conditional_logic import ConditionalLogic
    from tradingagents.graph.propagation import Propagator
    from langchain_core.tools import tool as lc_tool
    from langgraph.prebuilt import ToolNode

    mock_llm = _make_proper_mock_llm()

    @lc_tool
    def _dummy_tool(query: str) -> str:
        """Dummy tool for graceful degradation test."""
        return "dummy"

    dummy_tool_node = ToolNode([_dummy_tool])
    tool_nodes = {"market": dummy_tool_node}
    conditional_logic = ConditionalLogic(max_debate_rounds=1, max_risk_discuss_rounds=1)

    graph_setup = GraphSetup(
        quick_thinking_llm=mock_llm,
        deep_thinking_llm=mock_llm,
        tool_nodes=tool_nodes,
        bull_memory=MagicMock(),
        bear_memory=MagicMock(),
        trader_memory=MagicMock(),
        invest_judge_memory=MagicMock(),
        risk_manager_memory=MagicMock(),
        conditional_logic=conditional_logic,
    )

    config_dict = {
        "enable_options": True,
        "options_vendor": "tradier",
        "options_delta_target": 0.30,
        "options_dte_window": [21, 45],
        "options_min_oi": 100,
    }

    with patch("tradingagents.graph.setup.get_config", return_value=config_dict), \
         patch("tradingagents.graph.setup.OPTIONS_NODES", patched_nodes):
        compiled = graph_setup.setup_graph(selected_analysts=["market"])

    propagator = Propagator()
    init_state = propagator.create_initial_state("AAPL", "2025-01-15")
    args = propagator.get_graph_args()

    # Must not raise — graceful degradation
    with patch("tradingagents.dataflows.interface.route_to_vendor", side_effect=mock_route), \
         patch("tradingagents.agents.options.volatility_analyst.route_to_vendor", side_effect=mock_route), \
         patch("tradingagents.agents.options.options_flow_analyst.route_to_vendor", side_effect=mock_route), \
         patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf):
        final_state = compiled.invoke(init_state, **args)

    # Failed agent's field must be empty string (graceful fallback)
    assert final_state["options_flow_report"] == "", (
        f"options_flow_report must be empty when flow analyst fails, got: {final_state['options_flow_report']!r}"
    )

    # Upstream agent that succeeded must have non-empty output
    assert final_state["volatility_report"] != "", (
        "volatility_report must be non-empty (upstream agent succeeded before failure)"
    )

    # Equity pipeline must be unaffected
    assert final_state["market_report"] != "", "market_report must be non-empty (equity unaffected)"
