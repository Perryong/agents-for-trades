# Roadmap: TradingAgents — Options Extension

## Milestones

- **v1.0 Options Pipeline** — Phases 1-7 (shipped 2026-04-02)
- **v1.1 Stock Recommendation System** — Phases 8-12 (shipped 2026-04-03)
- **v1.2 Paper Trading & Validation** — Phases 13-16 (shipped 2026-04-03)
- **v1.0 Trade Recommendation Sidebar** — Phase 1 (shipped 2026-04-05)
- **v1.0 Analysis Progress & Cancellation** — Phase 1 (shipped 2026-04-07)
- **v2.0 Vol-Aware Analysis Pipeline** — Phases 17-19 (shipped 2026-04-09)

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

<details>
<summary>v1.0 Trade Recommendation Sidebar (Phase 1) — SHIPPED 2026-04-05</summary>

- [x] Phase 1: Trade Recommendation Sidebar & Lock-In Flow (6/6 plans) — completed 2026-04-05

See: `.planning/milestones/v1.0-ROADMAP.md` for full details.

</details>

<details>
<summary>v1.0 Analysis Progress & Cancellation (Phase 1) — SHIPPED 2026-04-07</summary>

- [x] Phase 1: Add analysis progress visibility and cancellation support (2/2 plans) — completed 2026-04-07

See: `.planning/milestones/v1.0-ROADMAP.md` for full details.

</details>

<details>
<summary>v2.0 Vol-Aware Analysis Pipeline (Phases 17-19) — SHIPPED 2026-04-09</summary>

- [x] Phase 17: Vol Context Backend (3/3 plans) — completed 2026-04-09
- [x] Phase 18: Analyst Prompt Integration (2/2 plans) — completed 2026-04-09
- [x] Phase 19: Frontend Restructure (2/2 plans) — completed 2026-04-09

See: `.planning/milestones/v2.0-ROADMAP.md` for full details.

</details>

## v3.0 Multi-Expiry Options Intelligence

### Phase 1: Multi-expiry options data for flow and vol analysts to support complex strategies

**Goal:** Expand options_flow_analyst and volatility_analyst to fetch chains across multiple DTE buckets (matching strike_expiry_selector's pattern), so the final decision agent has full term-structure context to recommend multi-leg strategies (iron condors, calendar spreads, straddles, etc.)
**Requirements**: [MEX-01, MEX-02, MEX-03, MEX-04, MEX-05]
**Depends on:** v2.0 shipped
**Plans:** 2/2 plans complete

Requirements:
- MEX-01: Extract DTE_BUCKETS to shared constants module, update strike_expiry_selector to import from it
- MEX-02: options_flow_analyst fetches chains across 4 DTE buckets, computes per-bucket flow metrics (P/C ratio, unusual activity, net bias), includes Term Structure Flow Summary in report
- MEX-03: volatility_analyst fetches chains across 4 DTE buckets, computes per-bucket IV/skew metrics, includes per-bucket term structure table in report
- MEX-04: Both agents label per-bucket metrics with DTE range and expiry date; buckets with no available expiry are noted as "No data" (not silently omitted)
- MEX-05: Individual bucket fetch failures do not block other buckets (error isolation per bucket)

Plans:
- [x] 01-01-PLAN.md — Extract DTE_BUCKETS to shared constants.py, update strike_expiry_selector
- [x] 01-02-PLAN.md — Refactor options_flow_analyst for multi-bucket flow metrics
- [ ] 01-03-PLAN.md — Refactor volatility_analyst for multi-bucket IV/skew metrics

### Phase 2: Strategy agent enhancement — registry-driven eligibility gate with declarative legs builder

**Goal:** Replace the 10-strategy hardcoded selector with a 40-strategy YAML registry, rule-based eligibility gate (hard gates + soft scoring), and declarative legs builder that eliminates all if/elif dispatch code
**Requirements**: [GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, REG-01, REG-02, REG-03, LEGS-01, LEGS-02, LEGS-03, SEL-01, SEL-02]
**Depends on:** Phase 1
**Plans:** 3 plans

Plans:
- [ ] 02-01-PLAN.md — Strategy registry YAML + Pydantic models + eligibility gate + tests (TDD)
- [ ] 02-02-PLAN.md — Strategy selector gate integration + AgentState update + test updates
- [ ] 02-03-PLAN.md — Declarative legs builder + strike/expiry selector anchor/width output + tests

---

*Roadmap created: 2026-03-31*
*v1.0 shipped: 2026-04-02*
*v1.1 shipped: 2026-04-03*
*v1.2 shipped: 2026-04-03*
*v1.0 sidebar shipped: 2026-04-05*
*v1.0 progress & cancellation shipped: 2026-04-07*
*v2.0 shipped: 2026-04-09*
