# Roadmap: TradingAgents — Options Extension

## Milestones

- **v1.0 Options Pipeline** — Phases 1-7 (shipped 2026-04-02)
- **v1.1 Stock Recommendation System** — Phases 8-12 (shipped 2026-04-03)
- **v1.2 Paper Trading & Validation** — Phases 13-16 (shipped 2026-04-03)
- **v1.0 Trade Recommendation Sidebar** — Phase 1 (shipped 2026-04-05)
- **v1.0 Analysis Progress & Cancellation** — Phase 1 (shipped 2026-04-07)
- **v2.0 Vol-Aware Analysis Pipeline** — Phases 17-19 (started 2026-04-09)

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

## v2.0 Vol-Aware Analysis Pipeline (Phases 17-19) — IN PROGRESS

- [x] **Phase 17: Vol Context Backend** — AgentState extension, Vol Context graph node, options always-on backend wiring (completed 2026-04-09)
- [x] **Phase 18: Analyst Prompt Integration** — All 5 analysts receive vol directive with per-role strength; vol_note field in output (completed 2026-04-09)
- [x] **Phase 19: Frontend Restructure** — Remove enable_options toggle, group tabs, collapsible vol banner, update node list (completed 2026-04-09)

### Phase Details

#### Phase 17: Vol Context Backend
**Goal**: The pipeline computes a vol narrative before analysts run and makes options always active, with no conditional gating in the graph
**Depends on**: Nothing (first phase of milestone)
**Requirements**: VOL-01, VOL-02, VOL-03, VOL-04, OPT-02, OPT-03
**Plans**: 3 plans

Plans:
- [x] 17-01-PLAN.md — AgentState vol fields + Vol Context node module (pure Python narrative builder)
- [x] 17-02-PLAN.md — Graph wiring: Vol Context into setup.py, progress.py, schemas.py (always-on options)
- [x] 17-03-PLAN.md — Frontend types: remove enable_options, add vol fields, PRE_NODES, group-based REPORT_TABS

**Success Criteria** (what must be TRUE):
  1. Running analysis against any ticker produces a vol context string in AgentState before any analyst node executes
  2. The progress stepper shows "Vol Context" as a named node that completes before analyst nodes appear
  3. If vol data fetch fails (e.g., no options chain for ticker), analysts still run and a failure flag is set in state — the pipeline does not abort
  4. Options pipeline always executes — no `enable_options` conditional block in setup.py or graph wiring
  5. `getNodeList()` returns the complete node set (equity + options + vol context) unconditionally — no runtime flag gates the list

#### Phase 18: Analyst Prompt Integration
**Goal**: All five equity analysts reason with vol awareness, with each analyst's system message calibrated to its vol relevance, and each analyst's output contains an auditable vol_note
**Depends on**: Phase 17 (vol_context field must exist in AgentState)
**Requirements**: ANALYST-01, ANALYST-02, ANALYST-03
**Plans**: 2 plans

Plans:
- [x] 18-01-PLAN.md — vol_note_utils helper + Market and Technical analyst vol injection (Strong/Moderate)
- [x] 18-02-PLAN.md — Social, News, and Fundamentals analyst vol injection (Moderate/Weak)

**Success Criteria** (what must be TRUE):
  1. Each analyst's output in the final JSON log contains a `vol_note` sentence (or a null/empty marker for weak-relevance analysts when vol context is absent)
  2. Market analyst output demonstrates reasoning about IV conditions — its `vol_note` references the vol directive ("Strong" weight)
  3. News and Fundamentals analyst outputs reference vol context only when relevant — their `vol_note` is present but brief, consistent with Weak directive strength
  4. When vol context fetch fails (Phase 17 fallback), analysts run without vol reference in their prompts and produce output without a vol_note — no prompt errors

#### Phase 19: Frontend Restructure
**Goal**: The frontend reflects that options are always on — the toggle is gone, tabs are visually grouped into Equity/Options/Decision sections, and vol context is visible at the top of every analyst report
**Depends on**: Phase 17 (types.ts node list changes), Phase 18 (vol_note field available for display)
**Requirements**: OPT-01, UI-01, UI-02, UI-03
**Plans**: 2 plans

Plans:
- [x] 19-01-PLAN.md — TypeScript fixes: remove enableOptions from App/ProgressStepper/ReportTabs, wire vol fields in useAnalysis
- [x] 19-02-PLAN.md — UI features: grouped tab section headers (EQUITY/OPTIONS/DECISION) + collapsible vol context banner

**Success Criteria** (what must be TRUE):
  1. ConfigSidebar contains no "Enable Options" toggle — opening the config panel shows no options-gating control
  2. Report tab area shows three visible section headers — "Equity", "Options", "Decision" — above the relevant tab groups
  3. Every analyst report tab (Market, Technical, Social, News, Fundamentals) displays a collapsible vol context banner at the top; the banner can be expanded and collapsed independently
  4. Vol context banner defaults to expanded on first view; a user who collapses it sees the analyst report content without the banner occupying space

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 17. Vol Context Backend | 3/3 | Complete    | 2026-04-09 |
| 18. Analyst Prompt Integration | 2/2 | Complete    | 2026-04-09 |
| 19. Frontend Restructure | 2/2 | Complete   | 2026-04-09 |

---

*Roadmap created: 2026-03-31*
*v1.0 shipped: 2026-04-02*
*v1.1 shipped: 2026-04-03*
*v1.2 shipped: 2026-04-03*
*v1.0 sidebar shipped: 2026-04-05*
*v1.0 progress & cancellation shipped: 2026-04-07*
*v2.0 started: 2026-04-09*
