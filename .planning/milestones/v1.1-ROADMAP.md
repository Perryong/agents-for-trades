# Roadmap: TradingAgents — Options Extension

## Milestones

- **v1.0 Options Pipeline** — Phases 1-7 (shipped 2026-04-02)
- **v1.1 Stock Recommendation System** — Phases 8-12 (active)

## Phases

<details>
<summary>v1.0 Options Pipeline (Phases 1-7) — SHIPPED 2026-04-02</summary>

- [x] Phase 1: Options Data Infrastructure (3/3 plans) — completed 2026-03-31
- [x] Phase 2: Volatility & Flow Agents (2/2 plans) — completed 2026-03-31
- [x] Phase 3: Strategy & Contract Selection Agents (2/2 plans) — completed 2026-03-31
- [x] Phase 4: Pricing, Order Building & Greeks (4/4 plans) — completed 2026-04-01
- [x] Phase 5: Graph Integration (2/2 plans) — completed 2026-04-01
- [x] Phase 6: Debator & Risk Manager Updates (2/2 plans) — completed 2026-04-01
- [x] Phase 7: Visual Frontend (5/5 plans) — completed 2026-04-01

See: `.planning/milestones/v1.0-ROADMAP.md` for full details.

</details>

---

### v1.1 Stock Recommendation System

- [x] **Phase 8: Screener Data Layer** — Programmatic market universe pre-filter with rate-limit-safe bulk fetch and session-boundary caching (completed 2026-04-02)
- [x] **Phase 9: LLM Screener Agent** — LLM ranker that accepts pre-filtered candidates and returns top 3-5 picks with rationale (completed 2026-04-02)
- [x] **Phase 10: Backend API Endpoint** — Synchronous `POST /api/screen` endpoint exposing screener results as JSON (completed 2026-04-02)
- [x] **Phase 11: Frontend Screener Tab** — WatchlistPanel component with ranked picks, timestamps, and select-to-analyze flow (completed 2026-04-02)
- [x] **Phase 12: CLI Integration** — `screen` subcommand displaying ranked picks in a Rich table (completed 2026-04-03)

---

## Phase Details

### Phase 8: Screener Data Layer
**Goal**: The screener can reliably fetch, filter, and cache market universe data without hitting rate limits or serving stale picks
**Depends on**: Nothing (self-contained data layer)
**Requirements**: SCREEN-01, SCREEN-02, SCREEN-03, SCREEN-04
**Success Criteria** (what must be TRUE):
  1. Running the pre-filter against a live market session returns a ranked candidate list of 20-50 tickers scored by volume, momentum, and unusual activity
  2. Requesting data twice within a market session returns cached results on the second call with no new yfinance fetches
  3. After market close, a new session open invalidates the cache and triggers a fresh fetch
  4. Fetching a universe of 500+ tickers completes without HTTP 429 errors, with coverage above 80% tracked and surfaced in the output
  5. Screener data is routed through the `VENDOR_METHODS` pattern under a `screener_data` category, with no direct yfinance imports outside `interface.py`
**Plans:** 2/2 plans complete
Plans:
- [x] 08-01-PLAN.md — Core screener module: bulk fetch, scoring, cache, Pydantic model, tests
- [x] 08-02-PLAN.md — VENDOR_METHODS integration wiring and integration tests

### Phase 9: LLM Screener Agent
**Goal**: The LLM screener agent ranks pre-filtered candidates and returns structured top picks that are fully isolated from the analysis pipeline state
**Depends on**: Phase 8
**Requirements**: RANK-01, RANK-02, RANK-03, RANK-04
**Success Criteria** (what must be TRUE):
  1. Calling `run_screener(config, llm)` with a list of up to 50 candidates returns a `ScreenerResult` containing 3-5 `TopPick` objects, each with ticker, score, rationale, confidence, and key metrics
  2. The `create_screener_agent` factory matches the `create_*` pattern and uses `quick_thinking_llm`
  3. `ScreenerResult` is never written to `AgentState` — passing the result through analysis pipeline entry raises a validation error
  4. The agent handles LLM response variation gracefully (malformed JSON, missing fields) without crashing
**Plans:** 1/1 plans complete
Plans:
- [x] 09-01-PLAN.md — Screener agent module: Pydantic models, factory, run_screener entry point, isolation guard, tests, __init__.py wiring

### Phase 10: Backend API Endpoint
**Goal**: The screener is accessible via a stable JSON API that is entirely independent from the analysis SSE stream
**Depends on**: Phase 9
**Requirements**: API-01, API-02
**Success Criteria** (what must be TRUE):
  1. `POST /api/screen` returns a JSON response containing ranked picks and a `screened_at` timestamp within 15 seconds
  2. The screener endpoint can be called while an analysis SSE stream is active with no interference in either direction
  3. The response shape matches the `ScreenResponse` Pydantic schema, verifiable with curl against a running FastAPI server
**Plans:** 1/1 plans complete
Plans:
- [x] 10-01-PLAN.md — Schemas, route handler, main.py wiring, and endpoint tests

### Phase 11: Frontend Screener Tab
**Goal**: Users can view ranked screener picks in the frontend and select one to pre-populate and launch the full analysis pipeline
**Depends on**: Phase 10
**Requirements**: FE-01, FE-02, FE-03
**Success Criteria** (what must be TRUE):
  1. The screener tab renders a `WatchlistPanel` listing up to 5 picks with ticker, score, rationale summary, and key metrics per pick
  2. Clicking "Analyze" on a screener pick pre-populates the analysis config with that ticker and the existing pipeline starts
  3. The `screened_at` timestamp is displayed prominently, with a stale indicator when results are older than the current session
**Plans**: TBD

### Phase 12: CLI Integration
**Goal**: Users can discover stock picks from the command line using the same screener logic as the frontend
**Depends on**: Phase 9
**Requirements**: CLI-01, CLI-02
**Success Criteria** (what must be TRUE):
  1. Running `python -m cli screen` displays a Rich table of ranked picks with columns for Ticker, Score, Confidence, Rationale, and key metrics
  2. Each row in the CLI table matches the same ranked output that the frontend and API would return for the same market session
**Plans:** 1/1 plans complete
Plans:
- [x] 12-01-PLAN.md — Screen subcommand with Rich table, --max-picks, --json flags, and tests

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 8. Screener Data Layer | 2/2 | Complete   | 2026-04-02 |
| 9. LLM Screener Agent | 1/1 | Complete   | 2026-04-02 |
| 10. Backend API Endpoint | 1/1 | Complete    | 2026-04-02 |
| 11. Frontend Screener Tab | 2/2 | Complete    | 2026-04-02 |
| 12. CLI Integration | 1/1 | Complete    | 2026-04-03 |

---

*Roadmap created: 2026-03-31*
*v1.0 shipped: 2026-04-02*
*v1.1 roadmap added: 2026-04-02*
