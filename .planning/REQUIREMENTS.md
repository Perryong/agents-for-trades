# Requirements: TradingAgents

**Defined:** 2026-04-03
**Core Value:** Trader receives a complete, executable options recommendation derived from the same AI analytical process that drives the equity decision

## v1.2 Requirements

Requirements for Paper Trading & Validation milestone. Each maps to roadmap phases.

### Charts (TradingView Lightweight Charts v5)

- [ ] **CHART-01**: User can view candlestick price chart for any analyzed ticker
- [ ] **CHART-02**: User can view volume bars below the candlestick chart
- [ ] **CHART-03**: User can see paper trade entry/exit markers overlaid on the chart
- [ ] **CHART-04**: User can toggle between daily, weekly, and monthly timeframes
- [ ] **CHART-05**: User can see per-agent bull/bear signal annotations at the decision point on the chart

### Execution (Alpaca Paper Trading)

- [ ] **EXEC-01**: User can configure Alpaca paper trading API keys via environment variables
- [ ] **EXEC-02**: User can auto-execute an equity BUY/SELL order from the agent's final decision
- [ ] **EXEC-03**: User can see order status (submitted/filled/rejected) in the frontend
- [ ] **EXEC-04**: User can auto-execute multi-leg options orders from the options legs builder output
- [ ] **EXEC-05**: System auto-closes paper positions after N days and computes outcome (WIN/LOSS/OPEN)

### Scoring (Recommendation Scoring)

- [ ] **SCORE-01**: Each trade decision stores outcome field (WIN/LOSS/OPEN) and P&L percentage
- [ ] **SCORE-02**: User can view win rate, expectancy, and aggregate P&L metrics
- [ ] **SCORE-03**: User can view confidence-calibration chart comparing stated confidence vs actual outcome rate

### Dashboard (Track Record)

- [ ] **DASH-01**: User can view summary statistics (win rate, total trades, P&L, avg gain/loss)
- [ ] **DASH-02**: User can view chronological trade history table with outcomes
- [ ] **DASH-03**: User can view equity curve chart showing running P&L over time
- [ ] **DASH-04**: User can view per-ticker accuracy breakdown
- [ ] **DASH-05**: User can view separate win rates for options vs equity decisions

## v1.3+ Requirements

Deferred to future release. Tracked but not in current roadmap.

### Scoring

- **SCORE-04**: User can view per-agent accuracy breakdown (which agents had most accurate signals)

### Backtesting

- **BACK-01**: User can replay historical decisions against price data
- **BACK-02**: User can compare agent performance across different market regimes

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Live/real-money Alpaca execution | Paper-only in v1.2; regulatory compliance and risk surface |
| TradingView Advanced Charting Library | Proprietary, requires application, 100kB+ overhead, overkill |
| TradingView iframe/embed widget | Cannot overlay custom data, agent signals, or trade markers |
| Portfolio rebalancing / position sizing | No persistent portfolio model; fixed paper order size |
| WebSocket real-time P&L streaming | REST polling sufficient for paper trading frequency |
| Multiple broker integrations | Alpaca only; vendor-abstract the interface for future |
| Social comparison / leaderboard | Single-user tool, no multi-user architecture |
| Natural language outcome entry | Auto-compute from price data instead |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CHART-01 | — | Pending |
| CHART-02 | — | Pending |
| CHART-03 | — | Pending |
| CHART-04 | — | Pending |
| CHART-05 | — | Pending |
| EXEC-01 | — | Pending |
| EXEC-02 | — | Pending |
| EXEC-03 | — | Pending |
| EXEC-04 | — | Pending |
| EXEC-05 | — | Pending |
| SCORE-01 | — | Pending |
| SCORE-02 | — | Pending |
| SCORE-03 | — | Pending |
| DASH-01 | — | Pending |
| DASH-02 | — | Pending |
| DASH-03 | — | Pending |
| DASH-04 | — | Pending |
| DASH-05 | — | Pending |

**Coverage:**
- v1.2 requirements: 18 total
- Mapped to phases: 0
- Unmapped: 18

---
*Requirements defined: 2026-04-03*
*Last updated: 2026-04-03 after initial definition*
