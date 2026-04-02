# Requirements: TradingAgents — Stock Recommendation System

**Defined:** 2026-04-02
**Core Value:** The trader receives a complete, executable options recommendation derived from the same AI analytical process that drives the equity decision

## v1.1 Requirements

Requirements for stock recommendation/screening system. Each maps to roadmap phases.

### Screener Data Layer

- [x] **SCREEN-01**: Programmatic pre-filter scans market universe via yfinance bulk download with chunked fetching and rate-limit safety
- [x] **SCREEN-02**: Pre-filter outputs scored candidate list (max 50) ranked by volume, momentum, and unusual activity signals
- [ ] **SCREEN-03**: Screener data routed through existing `VENDOR_METHODS` pattern with new `screener_data` category
- [x] **SCREEN-04**: Market-session-aware cache prevents stale data during trading hours and avoids unnecessary refetches after close

### LLM Screener Agent

- [ ] **RANK-01**: `create_screener_agent` factory follows existing `create_*` pattern, uses `quick_thinking_llm` for cost control
- [ ] **RANK-02**: LLM ranker accepts pre-filtered candidates (hard cap 50) and returns top 3-5 picks with rationale and confidence score
- [ ] **RANK-03**: Screener output uses dedicated `ScreenerResult` model — never written to `AgentState`
- [ ] **RANK-04**: Structured JSON output per pick: ticker, score, rationale, key metrics (volume, momentum, sector)

### Backend API

- [ ] **API-01**: `POST /api/screen` endpoint returns synchronous JSON with ranked picks and `screened_at` timestamp
- [ ] **API-02**: Screener endpoint is independent from analysis SSE stream — no coupling between screener and pipeline

### Frontend Integration

- [ ] **FE-01**: WatchlistPanel component displays ranked screener results with key metrics per pick
- [ ] **FE-02**: User can select a screener pick to pre-populate the analysis config and run the full pipeline
- [ ] **FE-03**: Stale data indicator shows `screened_at` timestamp prominently

### CLI Integration

- [ ] **CLI-01**: `screen` subcommand runs the screener and displays ranked results in a Rich table
- [ ] **CLI-02**: CLI output includes ticker, score, rationale summary, and key metrics per pick

## v2 Requirements

### Enhanced Screening

- **SCREEN-V2-01**: finvizfinance as alternative screener data vendor (richer filters, unusual volume detection)
- **SCREEN-V2-02**: Options-readiness flag on screener picks (IV rank, liquidity check)
- **SCREEN-V2-03**: Screener results persistence to JSON (consistent with trade decision logging)

### Backtesting

- **BACK-01**: Evaluate logged trade decisions against subsequent price action (equity)
- **BACK-02**: Synthetic options backtesting using Black-Scholes with historical IV
- **BACK-03**: Benchmark comparison against buy-and-hold S&P 500

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-running full pipeline on screened picks | LLM cost prohibitive — user selects which to analyze |
| finvizfinance dependency | Deferred to v2 — yfinance-only for v1.1 |
| Real-time streaming screener updates | Batch/on-demand only, consistent with existing pipeline |
| Backtesting engine | Deferred to v1.2 — need accumulated logged decisions first |
| Live order execution | Analysis and order generation only — no automated submission |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCREEN-01 | Phase 8 | Complete |
| SCREEN-02 | Phase 8 | Complete |
| SCREEN-03 | Phase 8 | Pending |
| SCREEN-04 | Phase 8 | Complete |
| RANK-01 | Phase 9 | Pending |
| RANK-02 | Phase 9 | Pending |
| RANK-03 | Phase 9 | Pending |
| RANK-04 | Phase 9 | Pending |
| API-01 | Phase 10 | Pending |
| API-02 | Phase 10 | Pending |
| FE-01 | Phase 11 | Pending |
| FE-02 | Phase 11 | Pending |
| FE-03 | Phase 11 | Pending |
| CLI-01 | Phase 12 | Pending |
| CLI-02 | Phase 12 | Pending |

**Coverage:**
- v1.1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-02 after v1.1 roadmap creation*
