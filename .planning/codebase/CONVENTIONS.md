# Coding Conventions

**Analysis Date:** 2026-03-31

## Naming Patterns

**Files:**
- Module files use `snake_case`: `trading_graph.py`, `agent_states.py`, `alpha_vantage_common.py`
- Files named after their primary abstraction: `bull_researcher.py` contains `create_bull_researcher`, `memory.py` contains `FinancialSituationMemory`
- Vendor-specific modules use prefix naming: `alpha_vantage_stock.py`, `alpha_vantage_news.py`, `yfinance_cache.py`

**Classes:**
- `PascalCase` throughout: `TradingAgentsGraph`, `FinancialSituationMemory`, `ConditionalLogic`, `StatsCallbackHandler`, `AlphaVantageRateLimitError`
- Abstract base classes named with `Base` prefix: `BaseLLMClient` in `tradingagents/llm_clients/base_client.py`
- Enums use `PascalCase` for class, `SCREAMING_SNAKE_CASE` for members: `AnalystType.MARKET`, `AnalystType.FUNDAMENTALS` in `cli/models.py`
- Custom exceptions use `Error` suffix: `AlphaVantageRateLimitError` in `tradingagents/dataflows/alpha_vantage_common.py`

**Functions:**
- `snake_case` for all functions and methods: `create_market_analyst`, `get_stock_data`, `route_to_vendor`
- Factory functions use `create_` prefix: `create_market_analyst()`, `create_bull_researcher()`, `create_msg_delete()`
- Private/internal helpers use `_` prefix: `_fetch()`, `_cache_root()`, `_is_stale()`, `_make_api_request()`, `_tokenize()`, `_rebuild_index()`
- Getter functions use `get_` prefix: `get_config()`, `get_llm()`, `get_memories()`, `get_stats()`

**Variables:**
- `snake_case` for all variables: `trade_date`, `company_of_interest`, `quick_thinking_llm`, `deep_thinking_llm`
- Constants use `SCREAMING_SNAKE_CASE`: `DEFAULT_CONFIG`, `VALID_MODELS`, `VENDOR_LIST`, `API_BASE_URL`, `MARKET_DATA_CACHE_TTL_SECONDS`
- Boolean flags prefer `snake_case` adjectives: `debug`, `is_stale`

**Type Annotations:**
- LangGraph state fields use `Annotated[type, "description"]` for both type hint and documentation: see `tradingagents/agents/utils/agent_states.py`
- Tool function parameters use `Annotated[str, "description string"]` to provide LLM-visible descriptions: see `tradingagents/agents/utils/core_stock_tools.py`

## Code Style

**Formatting:**
- No formatter configuration file detected (no `.flake8`, `pyproject.toml` `[tool.black]`, or `ruff` config)
- Standard Python indentation: 4 spaces
- String concatenation uses `f-strings` and `+` operator — both appear throughout the codebase

**Linting:**
- No linting configuration detected
- No `# type: ignore`, `# noqa`, or `# pylint: disable` comments found anywhere in the codebase
- Code is clean with no suppression pragmas

**Type Hints:**
- Used consistently on public method signatures in class-based code
- `Optional[str]`, `Dict[str, Any]`, `List[...]`, `Tuple[...]` from `typing` module
- `TypedDict` used for LangGraph state definitions: `InvestDebateState`, `RiskDebateState` in `tradingagents/agents/utils/agent_states.py`
- `ABC` and `@abstractmethod` used for the LLM client hierarchy: `tradingagents/llm_clients/base_client.py`

## Import Organization

**Order:**
1. Standard library imports (`os`, `json`, `time`, `hashlib`, `threading`, `re`, `pathlib`)
2. Third-party imports (`langchain_core`, `langgraph`, `yfinance`, `pandas`, `requests`, `rich`, `typer`, `pydantic`)
3. Internal package imports (relative `.` or absolute `tradingagents.*`)

**Path Style:**
- Intra-package imports use relative imports: `from .base_client import BaseLLMClient`, `from .config import get_config`
- Cross-package imports use absolute paths: `from tradingagents.graph.trading_graph import TradingAgentsGraph`
- Wildcard imports (`from tradingagents.agents import *`) used in `graph/setup.py` and `graph/trading_graph.py` to pull all agent factories

**Re-export / Aliasing:**
- Vendor implementations are re-exported with aliases at the interface layer (`tradingagents/dataflows/interface.py`): `get_fundamentals as get_yfinance_fundamentals`
- The `tradingagents/dataflows/interface.py` is the single public surface for all data access tools

## Error Handling

**Patterns:**
- `ValueError` raised for invalid configuration/inputs: `raise ValueError(f"Unsupported LLM provider: {provider}")` in `tradingagents/llm_clients/factory.py`
- `RuntimeError` raised when all vendor fallbacks exhausted: `raise RuntimeError(f"No available vendor for '{method}'")` in `tradingagents/dataflows/interface.py`
- Custom exception class `AlphaVantageRateLimitError(Exception)` used to signal rate-limit events and trigger vendor fallback logic in `tradingagents/dataflows/alpha_vantage_common.py`
- Silent fallback on corrupted cache: `except Exception: pass` in `tradingagents/dataflows/yfinance_cache.py` (line 65) — cache miss triggers fresh fetch
- Warning via `print()` for non-critical failures: `print(f"Warning: Failed to filter CSV data by date range: {e}")` in `tradingagents/dataflows/alpha_vantage_common.py`
- No general `except Exception` swallowing elsewhere; exceptions propagate naturally

**Strategy:**
- Vendor routing implements automatic fallback: primary vendors are tried first; `AlphaVantageRateLimitError` is the only condition that triggers fallback (other exceptions propagate)
- Date format errors surface via `datetime.strptime()` raising `ValueError` directly to callers

## Logging

**Framework:** `print()` — no logging framework (`logging` module) is used anywhere

**Patterns:**
- Debug output via `chunk["messages"][-1].pretty_print()` in `TradingAgentsGraph.propagate()` when `debug=True`
- Warning messages use `print(f"Warning: ...")` prefix
- No structured logging; no log levels

## Comments

**When to Comment:**
- Module-level docstrings used on modules with non-obvious purpose: `tradingagents/llm_clients/validators.py`, `tradingagents/agents/utils/memory.py`
- Inline `#` comments used to label logical groupings in long functions and config dicts
- Section separators with `#` used in `trading_graph.py` and `setup.py`

**Docstrings:**
- All public class methods have docstrings with `Args:` and `Returns:` sections following Google-style conventions
- Factory functions (e.g., `create_llm_client` in `tradingagents/llm_clients/factory.py`) have full docstrings including `Raises:`
- Inner closure functions (e.g., `market_analyst_node`, `bull_node`) have minimal or no docstrings
- LangChain `@tool` functions use docstrings as the LLM-visible tool description — these are load-bearing and must be kept accurate

## Function Design

**Size:**
- Public factory/class methods are short and delegate to inner closures or helper methods
- Inner closure pattern used for LangGraph nodes: `create_market_analyst()` returns `market_analyst_node`, `create_bull_researcher()` returns `bull_node`
- Agent prompt strings are long (50–100+ lines) but kept inside the function that uses them, not extracted to constants

**Parameters:**
- `**kwargs` used at LLM client boundaries to pass provider-specific args through the stack without explicit enumeration
- Default argument values used for optional config: `debug=False`, `config: Dict[str, Any] = None`, `callbacks: Optional[List] = None`
- LangGraph tool parameters use `Annotated[type, "description"]` — the description string is consumed by the LLM tool-calling framework

**Return Values:**
- Data access functions consistently return `str` (formatted text/CSV) for LLM consumption, never raw `pd.DataFrame`
- LangGraph node functions return `dict` with state keys to update
- Class methods on LLM clients return the LLM instance: `get_llm() -> Any`

## Module Design

**Exports:**
- `__init__.py` files used to re-export public symbols; `tradingagents/agents/__init__.py` exposes all `create_*` factory functions via wildcard
- Module-level constants (`DEFAULT_CONFIG`, `VENDOR_METHODS`, `TOOLS_CATEGORIES`) serve as configuration registries

**Barrel Files:**
- `tradingagents/dataflows/interface.py` acts as the single routing layer for all data tool calls — all agent tools import from here via `route_to_vendor()`
- `tradingagents/agents/utils/agent_utils.py` re-exports all tool functions from sub-modules as the agent layer's public API
- `cli/utils.py` imported with `*` in `cli/main.py` indicating it is a barrel for CLI utility functions

**Configuration Pattern:**
- Global mutable config singleton in `tradingagents/dataflows/config.py` with `get_config()` / `set_config()` / `initialize_config()`
- `DEFAULT_CONFIG` dict in `tradingagents/default_config.py` is the single source of truth for default values
- Config passed explicitly as `dict` into `TradingAgentsGraph.__init__()` and merged into the singleton via `set_config()`

---

*Convention analysis: 2026-03-31*
