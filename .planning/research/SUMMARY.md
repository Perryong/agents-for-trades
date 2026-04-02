# Project Research Summary

**Project:** TradingAgents v1.1 — Stock Screener / Recommendation System
**Domain:** AI-driven stock screener layered on an existing LangGraph multi-agent trading framework
**Researched:** 2026-04-02
**Confidence:** HIGH (architecture findings from direct codebase analysis; stack and pitfalls from verified sources)

---

## Executive Summary

TradingAgents v1.1 adds a stock screening capability on top of a well-structured v1.0 pipeline. The v1.0 system already handles single-ticker analysis via LangGraph agents, FastAPI SSE streaming, and a React frontend — all of which remain unchanged. The v1.1 screener is a discrete pre-analysis discovery layer: it narrows a universe of ~500 tickers to 20-50 candidates via programmatic signal filters, then uses a single LLM call to rank the top 3-5 picks with momentum rationale. A user selects one pick and fires the unchanged full analysis pipeline. The screener is NOT a second LangGraph graph — it is a standalone Python module that hands off to the existing pipeline.

The recommended approach keeps the dependency footprint minimal and the integration surface small. One new Python package (`finvizfinance>=1.3.0`) handles broad market universe scanning; all other data access reuses existing `yfinance` patterns via the established `route_to_vendor` vendor abstraction. No new npm packages are required for the frontend MVP. The screener module lives at `tradingagents/screener/` with clean boundaries: `pre_filter.py` (pure Python math), `llm_ranker.py` (single LLM call), `models.py` (dataclasses), and `data_fetcher.py` (vendor layer wrapper). A new `POST /api/screen` endpoint returns synchronous JSON — no SSE overhead needed for a 5-8 second operation.

The principal risks are cost and correctness. On cost: the pre-filter must hard-cap LLM input at 50 candidates — 200+ candidates inflates token spend to ~$54/month per user at GPT-4o pricing and degrades ranking quality simultaneously. On correctness: the screener must be strictly isolated from `AgentState` to prevent state contamination across analysis runs, and screener results must carry session-boundary TTL caching to prevent stale picks from being acted on. The screener must never auto-trigger the full analysis pipeline; all pipeline runs must require explicit per-ticker user confirmation.

---

## Key Findings

### Recommended Stack

The v1.0 stack (yfinance 0.2.63, stockstats 0.6.5, LangGraph, FastAPI, React 19 + TypeScript + Tailwind v4 + Vite 8) requires no replacements or upgrades. The sole new Python dependency is `finvizfinance>=1.3.0`, released January 2026 and actively maintained, which provides structured DataFrame output for broad market movers (unusual volume, top gainers/losers) with no API key requirement. `yfinance.screen()` exists in the current venv but has a known broken `size` parameter (GitHub issue #2419, April 2025) and serves only as a secondary fallback. Sector ETF momentum uses the existing `yf.download()` pattern over 11 SPDR ETF tickers — zero new dependency.

Frontend additions are pure React + Tailwind using patterns already in the codebase. `@tanstack/react-table` v8 is the right choice if the screener table grows beyond a basic sortable list, but is deferred for MVP (20-50 rows do not justify it).

**Core technologies (new additions only):**
- `finvizfinance>=1.3.0`: Broad market screener universe feed — no API key, structured DataFrames, actively maintained
- `yf.download()` (existing): Sector ETF momentum via 11 SPDR tickers — no new dependency
- `yf.screen()` (existing, fallback only): Market movers fallback — broken size param, use only if finvizfinance unavailable
- Native React + Tailwind (existing): Screener table UI — sufficient for 20-50 rows at MVP
- `@tanstack/react-table` v8 (deferred): Headless table with sort/filter — add only if table complexity grows

### Expected Features

The screener has a clear, narrow scope. The LLM's role is ranking and rationale, not filtering — programmatic filters gate the LLM. Features are ordered by implementation dependency.

**Must have (table stakes):**
- Market universe pre-filter — volume + market cap + RVol + price momentum in pure Python; narrows 500+ tickers to 20-50
- Minimum volume threshold (500K ADV) and minimum market cap ($500M) — eliminates illiquid and noise-heavy names
- Relative volume signal (RVol >= 2.0x 30-day average) — core momentum signal
- LLM screener agent ranking top 3-5 picks with per-pick rationale and HIGH/MEDIUM/LOW confidence flag
- Select-to-analyze integration — user clicks a pick, it pre-populates the existing analysis form; no backend state required
- CLI `screen` subcommand with Rich table output — screener must work from CLI, consistent with v1.0
- `POST /api/screen` endpoint returning synchronous JSON — mirrors existing `POST /api/analyze` structure

**Should have (differentiators):**
- Composite signal score (0-100) normalizing volume, momentum, and sector signals — enables visual ranking
- Sector momentum context — weight candidates from sectors with positive ETF momentum
- Options-readiness flag per pick — surface whether liquid options exist before user triggers full options analysis
- SSE streaming for screener progress — if latency exceeds 15 seconds, add using existing `ProgressCallbackHandler` pattern
- Screener results frontend tab with ranked card layout and prominent timestamps

**Defer to v1.2+:**
- Backtesting screener effectiveness (explicitly out of scope per PROJECT.md)
- Persistent watchlist / portfolio tracking
- Real-time intraday tick scanning (requires streaming data vendor not in current stack)
- Custom drag-and-drop filter builder UI
- Natural language filter input
- Social/news sentiment in pre-filter

### Architecture Approach

The screener is a standalone module at `tradingagents/screener/` — not a second `StateGraph`. This is the correct architectural decision: the analysis graph is a parallel fan-out/fan-in pipeline for a single ticker; the screener is a sequential batch scan of many tickers followed by one LLM call. LangGraph adds graph compilation overhead and forces the pre-filter (pure Python math) into a node invocation, which is wasteful and makes unit testing harder. The screener outputs a `ScreenerResult` dataclass that is consumed by the API endpoint and returned as JSON; it never enters `AgentState`. The handoff from screener to analysis is a user action, not an automated edge.

**Major components:**
1. `tradingagents/screener/pre_filter.py` — programmatic filters producing `list[CandidateTicker]`; no LLM dependency; testable in isolation
2. `tradingagents/screener/llm_ranker.py` — `create_llm_ranker` factory (matches existing `create_*` pattern); single LLM call; returns `ScreenerResult`
3. `tradingagents/screener/data_fetcher.py` — thin wrapper calling `route_to_vendor`; no direct yfinance imports
4. `tradingagents/screener/models.py` — `ScreenerConfig`, `CandidateTicker`, `TopPick`, `ScreenerResult` dataclasses
5. `api/routes.py` (modified) — `POST /api/screen` synchronous endpoint; `asyncio.to_thread` for blocking screener call
6. `frontend/src/components/WatchlistPanel.tsx` (new) — ranked card list; `onPickSelected(symbol)` callback wired to `App.tsx` ticker state
7. `tradingagents/dataflows/interface.py` (modified) — two new `VENDOR_METHODS` entries: `get_market_movers`, `get_sector_snapshot`

**Unchanged (do not touch):**
- `trading_graph.py`, `setup.py`, `agent_states.py`, all existing agents, `api/progress.py`

### Critical Pitfalls

1. **Screener auto-triggering the full analysis pipeline** — The screener must have no outgoing edges to analysis nodes. `ScreenerResult` must never enter `AgentState`. Frontend "Analyze" requires explicit per-ticker click. Add an API-layer guard rejecting `screener_mode + tickers > 1` with HTTP 422. Detection: screener run taking >60 seconds means the analysis pipeline is running.

2. **yfinance 429 errors silently corrupting screener output** — Never iterate individual tickers. Use `yf.download()` in chunks of 80-100 with `threads=True`. Implement exponential backoff (2s initial, 60s max, 3 retries per chunk). Track `fetch_attempted` vs `fetch_succeeded`; surface coverage percentage in API response; abort if coverage drops below 80%.

3. **Stale pre-filter data feeding the LLM** — Cache TTL must be tied to market session boundaries, not wall-clock time: 15-minute TTL during market hours (9:30-4:00 ET), reset at next session open otherwise. LLM prompt must include `data_as_of` timestamp. Frontend must display "Screened at [time]" prominently with a stale indicator.

4. **LLM receiving too many candidates** — Hard cap at 50 candidates entering the LLM step. This is a configuration constant enforced in the pre-filter output contract. Pre-filter criteria must produce 20-50 results from a 500-ticker universe (RVol >= 2.0x AND price >= $5 AND market cap >= $500M). If > 50 pass, apply secondary sort by RVol desc and truncate. Log `input_token_count` per screener LLM call; alert if > 15,000 tokens.

5. **AgentState contamination from screener fields** — Screener uses a separate `ScreenerState` TypedDict (or standalone dataclasses), never `AgentState`. Analysis pipeline state must be initialized fresh per ticker via `Propagator.create_initial_state()`. If `screener_*` keys appear in `AgentState` at pipeline entry, raise a validation error. Do not add speculative `screener_context` field to `AgentState` in v1.1.

---

## Implications for Roadmap

Based on research, the build must be dependency-ordered: data layer first (testable without LLM), then LLM ranker (testable with mock candidates), then API (testable with curl), then frontend (needs API contract), with CLI parallel to API.

### Phase 1: Screener Data Layer

**Rationale:** All downstream phases depend on the data layer being correct and rate-limit-safe. Building this first allows unit testing in isolation before any LLM spend is incurred. Pitfalls 2 and 3 (yfinance rate limits, stale cache) must be solved at this layer — they cannot be patched later.

**Delivers:** `get_yfinance_market_movers()`, `get_yfinance_sector_snapshot()` registered in `VENDOR_METHODS`; `screener_data: yfinance` in `default_config.py`; `models.py` dataclasses; `data_fetcher.py` vendor wrapper; `pre_filter.py` with chunk-based fetch, exponential backoff, coverage tracking, session-boundary TTL cache.

**Addresses:** Market universe pre-filter, volume/market cap/RVol/momentum filters (FEATURES.md table stakes)

**Avoids:** Pitfall 2 (yfinance 429 silent corruption), Pitfall 3 (stale data), Pitfall 8 (Tradier rate limits — apply options check after volume/price filter reduces to <=50 candidates)

**Gate:** Unit tests with mock yfinance data. Verify candidate output shape, filter thresholds, graceful skip on bad tickers, coverage metric in output.

### Phase 2: LLM Screener Agent

**Rationale:** Depends on Phase 1 models and data contracts. Built second so the prompt can be validated against real pre-filter output. The 50-candidate cap and prompt token budget must be defined here before the frontend builds expectations around output shape.

**Delivers:** `llm_ranker.py` with `create_llm_ranker` factory; `screener/__init__.py` with `run_screener(config, llm)` public entry point; minimal screener-specific prompt template (<= 300 token system prompt, no inherited options pipeline context).

**Addresses:** LLM agent ranking top 3-5 picks, per-pick rationale, confidence flag (FEATURES.md table stakes and differentiators)

**Avoids:** Pitfall 1 (no outgoing edges to analysis — screener is a module, not a graph), Pitfall 4 (50-candidate hard cap), Pitfall 5 (no `AgentState` fields added), Pitfall 6 (explicit momentum regime declared in prompt), Pitfall 10 (minimal prompt template)

**Gate:** Integration test with small fixed candidate list. Verify `ScreenerResult` parse is robust to LLM response variation.

### Phase 3: Backend API Endpoint

**Rationale:** Depends on Phase 2 `run_screener()` public interface. Defines the API contract that the frontend Phase 4 depends on. Using synchronous JSON (not SSE) keeps this phase simple and removes the `run_id` / `ProgressCallbackHandler` machinery for a 5-8 second operation.

**Delivers:** `ScreenRequest`, `ScreenResponse`, `TopPick` Pydantic schemas in `api/schemas.py`; `POST /api/screen` endpoint in `api/routes.py` using `asyncio.to_thread`; `screened_at` and `market_session` fields always in response envelope.

**Addresses:** Backend endpoint for screener (FEATURES.md table stakes)

**Avoids:** Pitfall 9 (timestamp in API envelope from day one), Pitfall 1 (API-layer guard rejecting auto-analysis)

**Gate:** `curl` test against running FastAPI server. Verify JSON shape matches `ScreenResponse`.

### Phase 4: Frontend Screener Tab

**Rationale:** Depends on Phase 3 API contract. State lifting for ticker selection in `App.tsx` is the most impactful frontend change — do it here rather than patching it later. Frontend must disable "Run Screener" during active analysis SSE stream to prevent state collision.

**Delivers:** `ScreenRequest` / `ScreenResponse` / `TopPick` types in `types.ts`; `useScreen.ts` fetch hook; `WatchlistPanel.tsx` with ranked card layout (max 5 picks, #1 visually prominent), prominent timestamp display, stale indicator; `App.tsx` modifications (screener tab, lifted ticker state, `onPickSelected` callback wiring).

**Addresses:** Screener results frontend tab, select-to-analyze integration (FEATURES.md table stakes and differentiators)

**Avoids:** Pitfall 9 (prominent timestamp + stale indicator), Pitfall 11 (disabled screener button during active analysis, separate state slice), Pitfall 12 (5-pick cap, ranked card layout, subdued CTAs on lower picks), Pitfall 13 (configurable thresholds in config sidebar)

**Gate:** Manual test: run screener from UI, verify picks render with timestamp, click "Analyze", verify existing analysis pipeline starts with correct ticker pre-populated.

### Phase 5: CLI Integration

**Rationale:** Depends on Phase 2 `run_screener()` only; independent of Phases 3-4 and can run in parallel with Phase 3 if needed. Low complexity — follows existing Typer + Rich patterns exactly.

**Delivers:** `screen` Typer subcommand in `cli/main.py` with Rich table output (Ticker, Score, Confidence, Rationale).

**Addresses:** CLI output for screener results (FEATURES.md table stakes)

**Gate:** `python -m cli screen --date 2026-04-02` returns table of picks.

---

### Phase Ordering Rationale

- Data layer first (Phase 1) ensures rate-limit safety and cache correctness are solved before any LLM spend is incurred — these cannot be fixed retroactively.
- LLM ranker second (Phase 2) because its output shape defines the API contract downstream phases depend on.
- API before frontend (Phase 3 before 4) because the frontend hook is blocked on a stable JSON schema.
- CLI parallel to or after Phase 2 because it only depends on `run_screener()`, not the API layer.
- This ordering matches ARCHITECTURE.md's recommended build sequence (Phase A through Phase E) exactly.

### Research Flags

Phases with standard, well-documented patterns (skip research-phase):
- **Phase 2 (LLM ranker):** `create_*` factory pattern is already established in codebase; single LLM call with structured output is well-understood
- **Phase 3 (API endpoint):** `POST /api/analyze` pattern is directly replicated; schemas follow existing Pydantic patterns
- **Phase 4 (Frontend):** `useAnalysis` hook is the direct model for `useScreen`; React state lifting is standard
- **Phase 5 (CLI):** Typer + Rich table is an existing pattern in the codebase

Phases likely needing closer attention during planning:
- **Phase 1 (Data layer):** `finvizfinance` scraping behavior needs validation against current Finviz HTML structure; yfinance bulk fetch chunking strategy needs performance testing against actual rate limit behavior post-2024 changes. Confidence is MEDIUM on finvizfinance stability.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | finvizfinance is scraping-based and can break on Finviz HTML changes; yfinance.screen() fallback has known broken params. All other stack findings are HIGH — existing codebase patterns verified by direct reading. |
| Features | HIGH | Feature scope is tightly constrained by PROJECT.md and the existing pipeline. Table stakes features are well-defined by domain standards. Anti-features are principled and backed by cost math. |
| Architecture | HIGH | All decisions derived from direct codebase reading. `route_to_vendor` pattern, `create_*` factory pattern, `AgentState` structure, API endpoint shape — all confirmed by source inspection. No external sources needed. |
| Pitfalls | HIGH | yfinance rate limits confirmed by GitHub issues and reproduction reports post-late-2024. Tradier rate limit from official docs. LLM cost math from official pricing. Pipeline auto-trigger risk directly from PROJECT.md scope declarations. |

**Overall confidence:** HIGH

### Gaps to Address

- **finvizfinance HTML stability:** The library scrapes Finviz HTML. If Finviz redesigns their screener page, the library breaks. Mitigation is already specified (yfinance fallback), but the fallback is also fragile. During Phase 1, validate that `finvizfinance.screener.overview.Overview` returns expected columns against the live site before committing to the screener data contract.

- **yfinance bulk fetch performance post-2024:** GitHub issues confirm rate limits tightened in late 2024 at ~950 tickers. The recommended chunk size (80-100 tickers) is conservative, but the exact limit is not officially documented. During Phase 1, instrument coverage tracking from the first run and tune chunk size empirically.

- **Options-readiness signal cost:** Checking options chain availability for 50 candidates at Tradier (120 req/min limit) is feasible if applied after the volume/price filter, but the exact latency hit needs measurement. Defer this feature to after core screener is stable (it is already in the "defer" category per FEATURES.md).

- **`finvizfinance` vs actual S&P 500 constituent list:** The library returns results based on Finviz's own index constituents, which may differ slightly from the canonical S&P 500. For v1.1 this is acceptable; for v1.2 backtesting, a canonical constituent list source will be needed.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase reading: `tradingagents/graph/setup.py`, `trading_graph.py`, `agent_states.py`, `dataflows/interface.py`, `api/routes.py`, `api/schemas.py`, `frontend/src/hooks/useAnalysis.ts`, `App.tsx` — confirmed all integration patterns
- `.planning/PROJECT.md` — v1.1 requirements and out-of-scope boundaries
- Tradier Rate Limiting — Official Docs: https://docs.tradier.com/docs/rate-limiting
- yfinance screener issue #2419 (broken size/offset): https://github.com/ranaroussi/yfinance/issues/2419
- yfinance rate limiting issues #2128, #2422, #2614: confirmed post-2024 tightening

### Secondary (MEDIUM confidence)

- finvizfinance PyPI (v1.3.0, January 2026): https://pypi.org/project/finvizfinance/
- finvizfinance screener docs: https://finvizfinance.readthedocs.io/en/latest/screener.html
- TanStack Table v8: https://tanstack.com/table/v8/docs/guide/sorting
- Survivorship bias in momentum rotational strategies (CAGR drop from 46% to 16%): https://www.priceactionlab.com/Blog/2019/11/survivorship-bias-in-backtests-of-momentum-rotational-strategies/
- LLM cost token strategies 2025: https://sparkco.ai/blog/optimize-llm-api-costs-token-strategies-for-2025

### Tertiary (LOW confidence)

- yfinance.screen() fallback — broken `size` param, unofficial API, fragile. Use only if finvizfinance unavailable.

---

*Research completed: 2026-04-02*
*Ready for roadmap: yes*
