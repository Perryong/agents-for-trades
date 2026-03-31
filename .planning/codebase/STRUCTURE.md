# STRUCTURE.md — Directory Layout and Organization

## Root Layout

```
agents-for-trades/
├── main.py                          # Standalone entry point / quick runner
├── test.py                          # Manual smoke test (single function call)
├── pyproject.toml                   # Project metadata, dependencies
├── requirements.txt                 # Pip requirements
├── uv.lock                          # uv lockfile
├── README.md                        # Project documentation
│
├── cli/                             # CLI interface (Typer)
│   ├── main.py                      # CLI entry point, commands
│   ├── config.py                    # CLI config management
│   ├── models.py                    # CLI data models
│   ├── stats_handler.py             # Stats/analysis display
│   ├── utils.py                     # CLI utilities
│   ├── announcements.py             # Announcement banners
│   └── __init__.py
│
├── tradingagents/                   # Core library
│   ├── default_config.py            # DEFAULT_CONFIG dict — all configurable knobs
│   │
│   ├── agents/                      # All LLM agent definitions
│   │   ├── analysts/                # 5 analyst agents (market, technical, social, news, fundamentals)
│   │   ├── managers/                # research_manager.py, risk_manager.py
│   │   ├── researchers/             # bull_researcher.py, bear_researcher.py
│   │   ├── risk_mgmt/               # aggressive_debator.py, conservative_debator.py, neutral_debator.py
│   │   ├── trader/                  # trader.py
│   │   ├── utils/
│   │   │   ├── agent_states.py      # AgentState, InvestDebateState, RiskDebateState TypedDicts
│   │   │   ├── agent_utils.py       # Shared @tool-decorated wrapper functions (abstract over vendors)
│   │   │   ├── memory.py            # FinancialSituationMemory (BM25)
│   │   │   ├── core_stock_tools.py
│   │   │   ├── fundamental_data_tools.py
│   │   │   ├── news_data_tools.py
│   │   │   ├── technical_indicators_tools.py
│   │   │   └── technical_pattern_tools.py
│   │   └── __init__.py              # Re-exports all create_* factory functions
│   │
│   ├── dataflows/                   # Data access layer
│   │   ├── interface.py             # Vendor router — maps tool name → vendor implementation
│   │   ├── config.py                # Runtime config accessor (set_config / get_config)
│   │   ├── y_finance.py             # yfinance implementations
│   │   ├── yfinance_cache.py        # CSV cache with TTL and corruption fallback
│   │   ├── yfinance_news.py         # yfinance news fetcher
│   │   ├── technical_analysis.py    # yfinance-based technical analysis
│   │   ├── stockstats_utils.py      # stockstats helpers
│   │   ├── alpha_vantage.py         # Alpha Vantage unified module
│   │   ├── alpha_vantage_common.py  # Shared AV helpers, rate limit error
│   │   ├── alpha_vantage_fundamentals.py
│   │   ├── alpha_vantage_indicator.py
│   │   ├── alpha_vantage_news.py
│   │   ├── alpha_vantage_stock.py
│   │   └── utils.py
│   │
│   ├── graph/                       # LangGraph orchestration
│   │   ├── trading_graph.py         # TradingAgentsGraph — top-level class
│   │   ├── setup.py                 # GraphSetup — builds StateGraph
│   │   ├── conditional_logic.py     # ConditionalLogic — routing functions
│   │   ├── propagation.py           # Propagator — state init and graph invocation
│   │   ├── reflection.py            # Reflector — post-trade memory updates
│   │   └── signal_processing.py    # SignalProcessor — extracts Buy/Sell/Hold
│   │
│   └── llm_clients/                 # LLM provider abstraction
│       ├── factory.py               # create_llm_client() factory
│       ├── base_client.py           # BaseLLMClient ABC
│       ├── openai_client.py         # OpenAI / Ollama / OpenRouter / xAI
│       ├── anthropic_client.py      # Anthropic Claude
│       ├── google_client.py         # Google Gemini
│       └── validators.py            # Model name allowlist
│
├── analysis_history/                # Persisted analysis outputs (gitignored data)
├── eval_results/                    # Trade decision logs per ticker
│   └── {TICKER}/
│       └── TradingAgentsStrategy_logs/
│           └── full_states_log_{date}.json
└── scripts/                         # Utility scripts
```

## Key Locations

| What you want | Where to look |
|---|---|
| Add a new analyst | `tradingagents/agents/analysts/` + register in `graph/setup.py` |
| Change LLM provider | `DEFAULT_CONFIG["llm_provider"]` in `default_config.py` |
| Add a new data vendor | `dataflows/interface.py` — add to `VENDOR_METHODS` |
| Change debate rounds | `DEFAULT_CONFIG["max_debate_rounds"]` |
| Modify agent prompts | Individual agent file in `agents/` subdirectories |
| Add new tool | `agents/utils/agent_utils.py` + register in `trading_graph.py._create_tool_nodes()` |
| Memory persistence | `agents/utils/memory.py` |

## Naming Conventions

- Agent factory functions: `create_{role_name}` (e.g., `create_market_analyst`, `create_aggressive_debator`)
- Graph node names: Title Case strings (e.g., `"Market Analyst"`, `"Risk Judge"`)
- State keys: `snake_case` (e.g., `market_report`, `risk_debate_state`)
- Config keys: `snake_case` in `DEFAULT_CONFIG` dict
- Data vendor modules: `{vendor_name}_{category}.py` (e.g., `alpha_vantage_news.py`)
