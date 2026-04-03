# Roadmap: TradingAgents — Options Extension

## Milestones

- **v1.0 Options Pipeline** — Phases 1-7 (shipped 2026-04-02)
- **v1.1 Stock Recommendation System** — Phases 8-12 (shipped 2026-04-03)
- **v1.2 Paper Trading & Validation** — Phases 13-16 (active)

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

### v1.2 Paper Trading & Validation

- [ ] **Phase 13: TradingView Chart Integration** — Candlestick, volume, timeframe, and agent signal charts rendered in the frontend
- [ ] **Phase 14: Alpaca Paper Trading Execution** — Equity and options order submission, status display, trade markers, and auto-close
- [ ] **Phase 15: Recommendation Scoring** — Trade outcome storage, win rate, expectancy, and confidence-calibration metrics
- [ ] **Phase 16: Track Record Dashboard** — Summary stats, trade history table, equity curve, per-ticker breakdown, and options vs equity split

---

## Phase Details

### Phase 13: TradingView Chart Integration
**Goal**: Users can visually orient any analyzed ticker with an interactive price chart showing candlesticks, volume, timeframes, and per-agent signal annotations
**Depends on**: Nothing (zero broker dependency; uses existing yfinance OHLCV data)
**Requirements**: CHART-01, CHART-02, CHART-04, CHART-05
**Success Criteria** (what must be TRUE):
  1. After running analysis on any ticker, user sees a candlestick price chart rendered below the signal banner
  2. User sees volume bars displayed below the candlestick chart on the same component
  3. User can click daily, weekly, or monthly toggle buttons and the chart re-renders to the selected timeframe
  4. User can see per-agent bull/bear signal annotations pinned at the decision date on the chart
**Plans**: TBD

### Phase 14: Alpaca Paper Trading Execution
**Goal**: Users can submit paper equity and options orders from the agent decision, see live order status, see fill markers on the chart, and have positions auto-closed after N trading days
**Depends on**: Phase 13 (chart component must exist for trade marker overlay)
**Requirements**: EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05, CHART-03
**Success Criteria** (what must be TRUE):
  1. User can configure Alpaca paper API keys via environment variables and the app starts without errors when keys are valid
  2. After analysis completes on an equity ticker, user can click "Execute Paper Trade" and see the order status change to submitted, filled, or rejected
  3. After a paper equity order fills, user sees a trade entry marker pinned at the fill price on the candlestick chart
  4. User can submit a multi-leg options paper order from the options legs builder output and see the order status reflected in the frontend
  5. After N trading days, the system auto-closes the paper position and records the outcome as WIN, LOSS, or OPEN
**Plans**: TBD

### Phase 15: Recommendation Scoring
**Goal**: Users can see quantitative evidence of system performance — win rate, expectancy, profit factor, and a confidence-calibration chart — derived from scored paper trade records
**Depends on**: Phase 14 (fill prices and outcome records must exist before scoring is meaningful)
**Requirements**: SCORE-01, SCORE-02, SCORE-03
**Success Criteria** (what must be TRUE):
  1. Each paper trade record stores outcome (WIN/LOSS/OPEN) and P&L percentage alongside fill price, target price, stop price, and decision date
  2. User can view win rate, expectancy, average winner, average loser, and profit factor together — never win rate as a standalone figure
  3. User can view a confidence-calibration chart that plots stated AI confidence against actual outcome rate across all scored trades
**Plans**: TBD

### Phase 16: Track Record Dashboard
**Goal**: Users can open a Track Record tab and see a complete, self-contained view of system performance — summary stats, chronological trade history, equity curve, per-ticker breakdown, and equity vs options split
**Depends on**: Phase 15 (scored trade records), Phase 13 (chart component reused for equity curve line series)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. User can open the Track Record tab and see summary stats cards: total trades, win rate, aggregate P&L, average gain, average loss — all with a persistent paper trading disclaimer
  2. User can scroll a chronological trade history table showing ticker, direction, entry date, outcome, and P&L for every paper trade
  3. User can see an equity curve chart that plots running P&L over time across all paper trades
  4. User can click into a per-ticker view and see win rate and P&L breakdown isolated to that ticker
  5. User can switch between equity-only and options-only performance views, each showing metrics appropriate to that asset class
**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 13. TradingView Chart Integration | 0/? | Not started | - |
| 14. Alpaca Paper Trading Execution | 0/? | Not started | - |
| 15. Recommendation Scoring | 0/? | Not started | - |
| 16. Track Record Dashboard | 0/? | Not started | - |

---

*Roadmap created: 2026-03-31*
*v1.0 shipped: 2026-04-02*
*v1.1 shipped: 2026-04-03*
*v1.2 roadmap added: 2026-04-03*
