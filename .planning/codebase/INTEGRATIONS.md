# External Integrations

**Analysis Date:** 2026-03-31

## APIs & External Services

**LLM Providers (one required at runtime):**

- **OpenAI** — default provider; powers `deep_think_llm` and `quick_think_llm` agents
  - SDK/Client: `langchain-openai` → `tradingagents/llm_clients/openai_client.py`
  - Auth: `OPENAI_API_KEY`
  - Base URL: `https://api.openai.com/v1` (overridable via `config["backend_url"]`)
  - Special handling: `UnifiedChatOpenAI` subclass strips `temperature`/`top_p` for GPT-5 family models

- **Anthropic** — Claude model family support
  - SDK/Client: `langchain-anthropic` → `tradingagents/llm_clients/anthropic_client.py`
  - Auth: `ANTHROPIC_API_KEY`

- **Google** — Gemini model family support
  - SDK/Client: `langchain-google-genai` → `tradingagents/llm_clients/google_client.py`
  - Auth: `GOOGLE_API_KEY`
  - Special handling: `NormalizedChatGoogleGenerativeAI` normalizes list content responses from Gemini 3 models; `thinking_level` → `thinking_budget` mapping for Gemini 2.5 vs Gemini 3

- **xAI (Grok)** — Grok model family support via OpenAI-compatible API
  - SDK/Client: `langchain-openai` (`OpenAIClient` with `provider="xai"`) → `tradingagents/llm_clients/openai_client.py`
  - Auth: `XAI_API_KEY`
  - Base URL: `https://api.x.ai/v1`

- **OpenRouter** — Multi-provider routing proxy via OpenAI-compatible API
  - SDK/Client: `langchain-openai` (`OpenAIClient` with `provider="openrouter"`) → `tradingagents/llm_clients/openai_client.py`
  - Auth: `OPENROUTER_API_KEY`
  - Base URL: `https://openrouter.ai/api/v1`

- **Ollama** — Local LLM serving via OpenAI-compatible API
  - SDK/Client: `langchain-openai` (`OpenAIClient` with `provider="ollama"`) → `tradingagents/llm_clients/openai_client.py`
  - Auth: None required (uses placeholder key `"ollama"`)
  - Base URL: `http://localhost:11434/v1`

**Market Data Providers:**

- **Yahoo Finance (yfinance)** — default data vendor for all categories
  - SDK/Client: `yfinance` library → `tradingagents/dataflows/y_finance.py`, `tradingagents/dataflows/yfinance_news.py`
  - Auth: None (public API)
  - Provides: OHLCV price history, technical indicators (via stockstats), fundamentals, balance sheet, cash flow, income statement, insider transactions, ticker news, global market news (via `yf.Search`)
  - Cache TTLs: market data 6h, fundamentals/financials 24h, insider transactions 12h, news 30m

- **Alpha Vantage** — optional alternative data vendor
  - SDK/Client: `requests` (raw HTTP) → `tradingagents/dataflows/alpha_vantage_common.py`
  - Auth: `ALPHA_VANTAGE_API_KEY`
  - Base URL: `https://www.alphavantage.co/query`
  - Provides: OHLCV (TIME_SERIES_DAILY_ADJUSTED), technical indicators, fundamentals, news, insider transactions
  - Rate limiting: raises `AlphaVantageRateLimitError` on API limit responses

## Data Storage

**Databases:**
- None detected. No database client libraries in use.

**File Storage:**
- Local filesystem cache at `tradingagents/dataflows/data_cache/yfinance/`
  - CSV files for DataFrame responses (stock price history, indicator data)
  - TXT files for text responses (news, fundamentals, financial statements)
  - Cache keyed by SHA-256 hash of request payload; staleness checked by file mtime
  - Implementation: `tradingagents/dataflows/yfinance_cache.py`
- Analysis results written to `eval_results/<TICKER>/TradingAgentsStrategy_logs/`
- Daily analysis history committed to `analysis_history/<TICKER>/<DATE>/` (summary.json, summary.md, full_states_log.json)

**Caching:**
- `redis` >=6.2.0 is listed as a dependency but no Redis imports exist in the current source. The active cache backend is local filesystem only (see File Storage above).

## Authentication & Identity

**Auth Provider:**
- None (no user authentication system)
- API keys for LLM providers and Alpha Vantage are the only credentials; loaded from `.env` via `python-dotenv`

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, Datadog, etc.)

**Logs:**
- `print()` statements throughout agents and dataflows for debug output
- `rich.console.Console` in the CLI for formatted terminal output
- Full agent state logs serialized to JSON at `eval_results/<TICKER>/TradingAgentsStrategy_logs/full_states_log_<DATE>.json`
- LangChain callbacks supported via `callbacks` parameter on `TradingAgentsGraph.__init__`; `cli/stats_handler.py` implements a `StatsCallbackHandler` for tracking LLM/tool call statistics

## CI/CD & Deployment

**Hosting:**
- Not deployed as a service; runs as a Python library / CLI tool

**CI Pipeline:**
- GitHub Actions: `.github/workflows/daily-analysis.yml`
  - Triggers: daily cron (`30 13 * * *` UTC = 21:30 SGT), `workflow_dispatch`, push to `.github/daily-analysis-trigger.txt`
  - Runtime: `ubuntu-latest`, Python 3.11
  - Steps: checkout → install deps → run analysis → commit results → upload artifacts
  - Results committed back to the repository under `analysis_history/` and `eval_results/`
  - Artifacts uploaded via `actions/upload-artifact@v4`

## Environment Configuration

**Required env vars (one LLM provider key mandatory):**
- `OPENAI_API_KEY` — for OpenAI provider (default)
- `ANTHROPIC_API_KEY` — for Anthropic provider
- `GOOGLE_API_KEY` — for Google Gemini provider
- `XAI_API_KEY` — for xAI Grok provider
- `OPENROUTER_API_KEY` — for OpenRouter provider
- `ALPHA_VANTAGE_API_KEY` — required only when `data_vendors` category is set to `"alpha_vantage"`

**Optional env vars:**
- `TRADINGAGENTS_RESULTS_DIR` — override default results output path (`./results`)

**Secrets location:**
- Local development: `.env` file (`.env.example` provided, `.env` gitignored by convention)
- CI: GitHub Actions repository secrets (`secrets.OPENAI_API_KEY`, etc.) and repository variables (`vars.LLM_PROVIDER`, `vars.QUICK_MODEL`, etc.)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None (Alpha Vantage and yfinance are polled; no push/webhook integrations)

---

*Integration audit: 2026-03-31*
