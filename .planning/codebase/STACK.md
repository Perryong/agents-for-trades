# Technology Stack

**Analysis Date:** 2026-03-31

## Languages

**Primary:**
- Python >=3.10 (CI uses 3.11) - All application code

**Secondary:**
- PowerShell - `scripts/run-daily-analysis-now.ps1` (local dev helper)

## Runtime

**Environment:**
- Python >=3.10 (declared in `pyproject.toml`); CI pins 3.11 via `actions/setup-python@v5`

**Package Manager:**
- `pip` for CI and local installs
- `uv` also present (`uv.lock` committed) — available as an alternative resolver
- Lockfile: `uv.lock` present and committed

## Frameworks

**Core:**
- `langgraph` >=0.4.8 - Multi-agent workflow graph orchestration (StateGraph, ToolNode, conditional edges)
- `langchain-core` >=0.3.81 - Base abstractions shared by all LangChain provider packages

**LLM Provider Adapters:**
- `langchain-openai` >=0.3.23 - OpenAI, xAI (Grok), Ollama, and OpenRouter via OpenAI-compatible API
- `langchain-anthropic` >=0.3.15 - Anthropic Claude models
- `langchain-google-genai` >=2.1.5 - Google Gemini models
- `langchain-experimental` >=0.3.4 - Experimental LangChain utilities

**CLI:**
- `typer` >=0.21.0 - CLI entrypoint at `tradingagents = "cli.main:app"`
- `rich` >=14.0.0 - Terminal UI rendering (panels, spinners, live displays, tables, markdown)
- `questionary` >=2.1.0 - Interactive prompts in CLI

**Data & Analysis:**
- `pandas` >=2.3.0 - DataFrame manipulation throughout data pipeline
- `yfinance` >=0.2.63 - Primary market data source (OHLCV, news, fundamentals, financials)
- `stockstats` >=0.6.5 - Technical indicator calculation on top of yfinance data
- `backtrader` >=1.9.78.123 - Listed dependency; no active import found in current source (likely reserved for backtesting evaluation)
- `parsel` >=1.10.0 - HTML/XPath parsing (used in scraping utilities)

**Retrieval / Memory:**
- `rank-bm25` >=0.2.2 - BM25 lexical similarity for the `FinancialSituationMemory` system (`tradingagents/agents/utils/memory.py`); fully offline, no embeddings API required

**Utilities:**
- `requests` >=2.32.4 - HTTP client for Alpha Vantage REST API calls
- `tqdm` >=4.67.1 - Progress bars
- `pytz` >=2025.2 - Timezone handling
- `typing-extensions` >=4.14.0 - Backported typing features
- `setuptools` >=80.9.0 - Build backend

## Key Dependencies

**Critical:**
- `langgraph` >=0.4.8 - Entire agent execution model depends on this; drives `StateGraph` compilation in `tradingagents/graph/setup.py`
- `langchain-openai` / `langchain-anthropic` / `langchain-google-genai` - Provider-specific LLM backends; provider selected at runtime via `config["llm_provider"]`
- `yfinance` >=0.2.63 - Default and fallback data source for all market data, fundamentals, and news

**Infrastructure:**
- `redis` >=6.2.0 - Listed as a dependency but no active Redis imports found in the current codebase; likely reserved for future distributed caching
- `python-dotenv` - Imported in `main.py` and `cli/main.py` via `dotenv.load_dotenv()`; not listed in `pyproject.toml` — installed separately in CI (`pip install -r requirements.txt python-dotenv`)

## Configuration

**Environment:**
- Runtime config via `tradingagents/default_config.py` (`DEFAULT_CONFIG` dict)
- Environment variables loaded from `.env` file via `python-dotenv`
- Key runtime settings: `llm_provider`, `deep_think_llm`, `quick_think_llm`, `backend_url`, `max_debate_rounds`, `max_risk_discuss_rounds`, `data_vendors`
- Data cache path: `tradingagents/dataflows/data_cache/` (local filesystem, CSV and TXT files)
- Results path: `./results` (overridable via `TRADINGAGENTS_RESULTS_DIR` env var)

**Build:**
- `pyproject.toml` — setuptools build system, package discovery for `tradingagents*` and `cli*`
- No frontend build step; pure Python package

## Platform Requirements

**Development:**
- Python >=3.10
- At least one LLM provider API key (see INTEGRATIONS.md)
- Internet access for yfinance (default) or Alpha Vantage (optional) data

**Production / CI:**
- GitHub Actions runner: `ubuntu-latest`
- Python 3.11 pinned in `.github/workflows/daily-analysis.yml`
- No containerization detected; runs directly on the Actions runner

---

*Stack analysis: 2026-03-31*
