# Roadmap: TradingAgents — Options Extension

## Milestones

- **v1.0 Options Pipeline** — Phases 1-7 (shipped 2026-04-02)
- **v1.1 Stock Recommendation System** — Phases 8-12 (shipped 2026-04-03)
- **v1.2 Paper Trading & Validation** — Phases 13-16 (shipped 2026-04-03)

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

<details>
<summary>v1.1 Stock Recommendation System (Phases 8-12) — SHIPPED 2026-04-03</summary>

- [x] Phase 8: Screener Data Layer (2/2 plans) — completed 2026-04-02
- [x] Phase 9: LLM Screener Agent (1/1 plans) — completed 2026-04-02
- [x] Phase 10: Backend API Endpoint (1/1 plans) — completed 2026-04-02
- [x] Phase 11: Frontend Screener Tab (2/2 plans) — completed 2026-04-02
- [x] Phase 12: CLI Integration (1/1 plans) — completed 2026-04-03

See: `.planning/milestones/v1.1-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.2 Paper Trading & Validation (Phases 13-16) — SHIPPED 2026-04-03</summary>

- [x] Phase 13: TradingView Chart Integration (3/3 plans) — completed 2026-04-03
- [x] Phase 14: Alpaca Paper Trading Execution (3/3 plans) — completed 2026-04-03
- [x] Phase 15: Recommendation Scoring (2/2 plans) — completed 2026-04-03
- [x] Phase 16: Track Record Dashboard (2/2 plans) — completed 2026-04-03

See: `.planning/milestones/v1.2-ROADMAP.md` for full details.

</details>

### Phase 1: Trade Recommendation Sidebar & Lock-In Flow

**Goal:** Replace the bottom ChartActionPanel with a brokerage-style right sidebar displaying editable AI trade recommendations, live prices, and bracket order execution (entry + OCO take-profit + stop-loss). Remove the 5-day auto-close system. Track close reasons and extend the dashboard with risk-reward and R-multiple metrics.
**Requirements:** [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12, D-13, D-14, D-15, D-16, D-17, D-18, D-19]
**Depends on:** v1.2 (Phases 13-16)
**Plans:** 3/6 plans executed

Plans:
- [x] 01-00-PLAN.md — Wave 0 test infrastructure: 10 test stubs across 4 files for Nyquist compliance
- [x] 01-01-PLAN.md — Backend data layer: DB migration, schemas, live price endpoint, AI structured JSON
- [x] 01-02-PLAN.md — Frontend types and hooks: BracketOrderParams, LivePriceData, useLivePrice, useTrade bracket support
- [x] 01-03-PLAN.md — Bracket order execution: bracket submission, close-reason detection, manual close, remove auto-close
- [ ] 01-04-PLAN.md — TradeSidebar UI: new sidebar component, ChartScreen layout restructure, delete old components
- [ ] 01-05-PLAN.md — Dashboard extensions: risk-reward, R-multiple, close-reason column, legacy data cleanup

---

*Roadmap created: 2026-03-31*
*v1.0 shipped: 2026-04-02*
*v1.1 shipped: 2026-04-03*
*v1.2 shipped: 2026-04-03*
