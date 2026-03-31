# CONCERNS.md — Technical Debt, Known Issues, and Areas of Concern

## Security

### API Key Handling
- **Risk: HIGH** — All API keys loaded via `dotenv` / `os.getenv`. No validation that keys are present before making API calls — failures surface as cryptic provider errors rather than clear config errors.
- **Files:** `tradingagents/default_config.py`, any file calling `os.getenv("OPENAI_API_KEY")` etc.
- **Mitigation needed:** Startup validation that required keys exist for the configured provider.

### No Input Sanitization
- **Risk: MEDIUM** — Ticker symbols and dates passed directly into LLM prompts and API calls. A malformed ticker could cause unexpected behavior in prompt construction.
- **Files:** `tradingagents/graph/propagation.py`, all analyst agent files

## Reliability & Fragility

### Silent Fallback on Rate Limit
- **Risk: HIGH** — `AlphaVantageRateLimitError` triggers silent fallback to yfinance. The user gets a result but may not know data came from a different source with different semantics.
- **File:** `tradingagents/dataflows/interface.py`

### BM25 Index Rebuild on Every Addition
- **Risk: MEDIUM** — `FinancialSituationMemory._rebuild_index()` reconstructs the full BM25 index every time `add_situations()` is called. With large memory stores this becomes O(n) per insertion.
- **File:** `tradingagents/agents/utils/memory.py`

### Memory is In-Process Only
- **Risk: MEDIUM** — All 5 `FinancialSituationMemory` instances are in-memory only. Restarting the process loses all accumulated trade memory. `reflect_and_remember()` is never called in `main.py` (commented out).
- **File:** `tradingagents/graph/trading_graph.py` (line: `# ta.reflect_and_remember(1000)`)

### CSV Cache Corruption Fallback is Silent
- **Risk: MEDIUM** — `yfinance_cache.py` catches CSV parse errors and re-fetches, but logs nothing. Repeated corruption goes undetected.
- **File:** `tradingagents/dataflows/yfinance_cache.py`

### Debate Round Counter Off-By-One Sensitivity
- **Risk: MEDIUM** — `should_continue_debate` checks `count >= 2 * max_debate_rounds`. The `3 * max_risk_discuss_rounds` check for risk analysis requires exactly 3 agents to rotate. Adding a 4th risk analyst would break the routing logic.
- **File:** `tradingagents/graph/conditional_logic.py`

## Code Quality / Tech Debt

### `langchain_openai.ChatOpenAI` Import in setup.py
- **Risk: LOW** — `setup.py` imports `ChatOpenAI` from `langchain_openai` in its type hint even though clients are now abstracted behind `BaseLLMClient`. This creates a hidden OpenAI dependency in the graph layer.
- **File:** `tradingagents/graph/setup.py`

### `main.py` Uses Hardcoded Model Names
- **Risk: LOW** — `main.py` hardcodes `"gpt-5-mini"` for both `deep_think_llm` and `quick_think_llm`, overriding `DEFAULT_CONFIG` defaults. Easy to forget when changing providers.
- **File:** `main.py`

### No Structured Output / Response Parsing
- **Risk: MEDIUM** — Agent decisions (Buy/Sell/Hold) are extracted from free-text LLM output by `SignalProcessor`. If the LLM formats its answer differently the signal extraction may fail silently, defaulting to an unclear result.
- **File:** `tradingagents/graph/signal_processing.py`

### Analyst Selection Order Determines Graph Topology
- **Risk: LOW** — The order of `selected_analysts` list directly determines graph edge wiring in `setup.py`. This is implicit and easy to break — no validation that the order is meaningful.
- **File:** `tradingagents/graph/setup.py`

### Prompt Strings Embedded Inline
- **Risk: LOW** — All agent system prompts are multi-line f-strings embedded directly in agent factory functions. No prompt management, versioning, or templating system.
- **Files:** All files in `tradingagents/agents/`

## Performance

### No Async Execution
- **Risk: MEDIUM** — All analysts run sequentially in the LangGraph DAG despite being independent. Analysts could run in parallel (LangGraph supports fan-out), potentially halving wall-clock time for a 5-analyst run.

### No Request Batching or Caching for LLM Calls
- **Risk: LOW** — Each agent makes fresh LLM calls with no caching. Identical prompts (e.g., same ticker/date run twice) make full API round-trips.

## Missing Infrastructure

| Gap | Impact |
|-----|--------|
| No test suite | Changes to agents or data layer have no regression safety net |
| No logging framework | Errors surface as exceptions; no structured log trail |
| No type checking enforced (mypy/pyright not configured) | State dict keys typos fail at runtime |
| No CI pipeline | No automated quality gate on PRs |
| Memory not persisted to disk | All reflection learning lost on restart |
