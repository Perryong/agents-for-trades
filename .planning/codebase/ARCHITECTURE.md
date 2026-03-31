# ARCHITECTURE.md — System Design and Patterns

## Pattern

**Multi-agent pipeline orchestrated by LangGraph StateGraph.**

The system uses a directed acyclic graph (DAG) with conditional edges to route state through a sequence of specialized AI agents. Each agent reads from and writes to a shared `AgentState` dict. No direct agent-to-agent communication — all data flows via state.

## High-Level Flow

```
START
  └─► Analyst(s) [parallel in config, sequential in graph]
        Each analyst: LLM ↔ ToolNode loop until no more tool calls
        Then: Msg Clear node (prunes messages to avoid context bloat)
  └─► Bull Researcher ↔ Bear Researcher  [debate loop, N rounds]
  └─► Research Manager (Investment Judge)
  └─► Trader
  └─► Aggressive Analyst ↔ Conservative Analyst ↔ Neutral Analyst  [risk debate, N rounds]
  └─► Risk Judge
  └─► END
```

## Layers

### 1. Entry Point
- `main.py` — standalone runner, creates `TradingAgentsGraph`, calls `propagate(ticker, date)`
- `cli/main.py` — CLI interface (Typer), same API

### 2. Graph Orchestration (`tradingagents/graph/`)
| File | Responsibility |
|------|---------------|
| `trading_graph.py` | `TradingAgentsGraph` class — initializes LLMs, memory, tool nodes, wires components |
| `setup.py` | `GraphSetup` — builds and compiles the LangGraph `StateGraph` |
| `conditional_logic.py` | `ConditionalLogic` — routing decisions (tool call loops, debate round counts) |
| `propagation.py` | `Propagator` — creates initial state, invokes graph |
| `reflection.py` | `Reflector` — post-trade memory updates for each agent role |
| `signal_processing.py` | `SignalProcessor` — extracts Buy/Sell/Hold from final LLM output |

### 3. Agent Layer (`tradingagents/agents/`)
| Subdirectory | Agents |
|---|---|
| `analysts/` | Market, Technical, Social Media, News, Fundamentals |
| `researchers/` | Bull Researcher, Bear Researcher |
| `managers/` | Research Manager (invest judge), Risk Manager (risk judge) |
| `risk_mgmt/` | Aggressive Debator, Conservative Debator, Neutral Debator |
| `trader/` | Trader |
| `utils/` | Agent state definitions, shared tool wrappers, memory, core tools |

Each agent is a **factory function** (`create_*`) returning a node closure that takes `AgentState` and returns a state delta dict.

### 4. Data Layer (`tradingagents/dataflows/`)
- **Vendor abstraction**: `interface.py` routes tool calls to the configured vendor (yfinance or alpha_vantage) based on `data_vendors` config categories
- **Tool-level override**: `tool_vendors` config key overrides category default per tool
- **Caching**: `yfinance_cache.py` — CSV cache with TTL staleness check and corruption fallback
- **Fallback chain**: Alpha Vantage tools fall back to yfinance on `AlphaVantageRateLimitError`

### 5. LLM Client Layer (`tradingagents/llm_clients/`)
- `factory.py` — `create_llm_client(provider, model, ...)` factory
- `base_client.py` — `BaseLLMClient` ABC
- Concrete clients: `OpenAIClient`, `AnthropicClient`, `GoogleClient`
- Provider aliases: `openai`, `ollama`, `openrouter`, `xai` → `OpenAIClient`; `anthropic` → `AnthropicClient`; `google` → `GoogleClient`
- `validators.py` — static allowlist for model validation

## State Schema

Two nested state objects within `AgentState`:

```python
AgentState:
  company_of_interest: str
  trade_date: str
  messages: List[BaseMessage]         # LangGraph message list (pruned between analyst phases)
  market_report / technical_report / sentiment_report / news_report / fundamentals_report: str
  investment_debate_state: InvestDebateState
    bull_history / bear_history / history: str
    current_response: str
    judge_decision: str
    count: int
  trader_investment_plan / investment_plan: str
  risk_debate_state: RiskDebateState
    aggressive_history / conservative_history / neutral_history / history: str
    latest_speaker: str
    judge_decision: str
    count: int
  final_trade_decision: str
```

## Memory System

`FinancialSituationMemory` — BM25-based lexical retrieval (no API, no embeddings, offline-capable).

- Each major agent role has its own memory instance (bull, bear, trader, invest_judge, risk_manager)
- `add_situations([(situation, recommendation)])` — adds and rebuilds BM25 index
- `get_memories(situation, n_matches=2)` — tokenizes query, scores against index, returns top-N
- `reflect_and_remember(returns)` — called post-trade to store lessons, keyed by P&L outcome

## Key Design Decisions

- **Configurable analyst set**: `selected_analysts` param controls which analysts run and in what order
- **Two LLMs**: `deep_think_llm` for judges/managers, `quick_think_llm` for analysts/researchers
- **Message pruning**: `Msg Clear` nodes delete messages between analyst phases to prevent context overflow
- **Debate rounds**: `max_debate_rounds` and `max_risk_discuss_rounds` config keys control loop depth
- **State logging**: Every run logs full state to `eval_results/{ticker}/TradingAgentsStrategy_logs/`
