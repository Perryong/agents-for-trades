# Sprint Change Proposal: Phase 2 — Screeners, Regime Detection & Exposure Management

**Date:** 2026-04-16
**Author:** Bok
**Change Type:** Strategic Expansion (Phase 2)
**Scope:** Major — New epics, PRD update, architecture extensions

---

## 1. Issue Summary

**Trigger:** MVP (Epics 1-8) is complete. The PRD defines Phase 2 features that are now ready for implementation. Additionally, the `claude-trading-skills` GitHub repo (tradermonty/claude-trading-skills) provides proven trading skill implementations that should be integrated as new screener strategies and market regime analysis capabilities.

**Context:**
- All 26 MVP stories across Epics 1-8 are implemented and in review
- The PRD Phase 2 explicitly planned: HMM regime detection, shared data layer, scheduled runs, real-time monitoring, enhanced dashboard, portfolio awareness
- The claude-trading-skills repo offers 40+ trading skills, of which ~15 are directly relevant
- The current Screener tab has a single momentum+volume strategy; users need multiple screening approaches

---

## 2. Impact Analysis

### Epic Impact
- **Epics 1-8:** No changes needed. Complete and stable.
- **New Epics 9-13:** Required to cover Phase 2 scope.

### PRD Impact
- Phase 2 section needs expansion with specific screener strategies and regime detection approach
- The HMM approach can be replaced/augmented by LLM-powered regime detection from claude-trading-skills (Macro Regime Detector, Exposure Coach)
- New FRs needed for multiple screeners, regime signals, and exposure management

### Architecture Impact
- New service: `tradingagents/services/regime_detector.py` — market regime classification
- New service: `tradingagents/services/exposure_manager.py` — capital allocation per regime
- Screener registry pattern: multiple screener strategies behind a common interface
- New API endpoints for screener strategy selection and regime status
- Frontend: Screener tab redesign with strategy picker

### UX Impact
- Screener tab: strategy selector dropdown/tabs (Momentum, VCP, CANSLIM, Earnings, Custom Watchlist)
- New regime indicator in header/status bar showing current market posture
- Exposure guidance integrated into recommendations (risk judge uses regime context)

---

## 3. Recommended Approach

**Direct Adjustment** — Add 5 new epics (9-13) to the existing plan. No rollback or MVP scope change needed.

**Rationale:**
- MVP is complete and working — Phase 2 is purely additive
- The claude-trading-skills repo provides proven implementations to adapt, not build from scratch
- Screener expansion is the highest-value Phase 2 feature (directly improves ticker selection)
- Regime detection feeds the risk judge (improves recommendation quality)
- Sequential epic structure allows incremental delivery

---

## 4. Proposed New Epics

### Epic 9: Multiple Screener Strategies (6 stories)

Expand the Screener tab with multiple screening approaches. Each strategy becomes a selectable mode.

| Story | Title | Description |
|-------|-------|-------------|
| 9.1 | Screener Registry and Strategy Interface | Create a registry pattern for screener strategies. Each strategy implements a common interface: `screen(config) → ScreenerResult`. Strategy selection via config/API. |
| 9.2 | VCP Screener Strategy | Implement Minervini's Volatility Contraction Pattern. Stage 2 uptrend detection, contraction analysis, pivot point calculation. Adapted from claude-trading-skills VCP Screener. |
| 9.3 | CANSLIM Growth Screener Strategy | Implement O'Neil's CANSLIM methodology (6/7 components). Current earnings, annual growth, new highs, supply/demand, institutional sponsorship, market direction. |
| 9.4 | Earnings Momentum Screener Strategy | Post-earnings gap analysis + PEAD pattern detection. 5-factor scoring: gap size, pre-earnings trend, volume, MA200/MA50 position. |
| 9.5 | Custom Watchlist Screener | Screen only tickers from the user's configured watchlist (from Epic 6 config). Apply the same signal scoring but on a focused universe. |
| 9.6 | Screener Tab UI Redesign | Strategy picker in Screener tab (dropdown or sub-tabs). Each strategy shows its specific metrics. Configurable max_picks and universe. |

**FRs covered:** FR28 (watchlist), new FR39-FR43 (multiple screening strategies)

### Epic 10: Market Regime Detection (4 stories)

Replace raw HMM with LLM-powered regime detection using market breadth, cross-asset analysis, and macro signals.

| Story | Title | Description |
|-------|-------|-------------|
| 10.1 | Market Breadth Scoring Service | 6-component breadth scoring (0-100): overall breadth, sector participation, sector rotation, momentum, mean reversion risk, historical context. Uses yfinance data. |
| 10.2 | Macro Regime Detector | Cross-asset ratio analysis: RSP/SPY concentration, yield curve, credit conditions, size factor, equity-bond relationship, sector rotation. Outputs regime classification (Concentration, Broadening, Contraction, Inflationary, Transitional). |
| 10.3 | Regime Signal as Agent Input | Feed regime classification as context to the risk judge. AgentSignal from regime detector follows standard protocol. Risk judge weights recommendations based on regime (e.g., reduce exposure in Contraction). |
| 10.4 | Regime Indicator in Frontend | Show current regime in header bar or status bar. Color-coded badge: green (Broadening), amber (Concentration/Transitional), red (Contraction). Historical regime timeline in Track Record. |

**FRs covered:** PRD Phase 2 HMM requirement (adapted), new FR44-FR47

### Epic 11: Exposure Management & Market Timing (4 stories)

Answer "how much capital should I commit?" before individual stock analysis.

| Story | Title | Description |
|-------|-------|-------------|
| 11.1 | Exposure Coach Service | Synthesize breadth + regime + top/bottom signals → exposure ceiling (0-100%), growth-vs-value bias, participation assessment. Outputs: NEW_ENTRY_ALLOWED, REDUCE_ONLY, or CASH_PRIORITY. |
| 11.2 | Market Top Detector | Distribution day counting (O'Neil method), leading stock deterioration, defensive rotation signals. Feeds into Exposure Coach. |
| 11.3 | FTD Bottom Detector | Follow-Through Day signal for market bottom confirmation. Dual-index tracking (S&P + NASDAQ). State machine for rally attempt → FTD → post-FTD monitoring. |
| 11.4 | Exposure-Aware Risk Judge | Risk judge receives exposure ceiling from Exposure Coach. Recommendations are gated: if REDUCE_ONLY, only exit/hedge recommendations. If CASH_PRIORITY, no new entries. |

**FRs covered:** FR14-FR18 (risk management, enhanced), new FR48-FR51

### Epic 12: Scheduled Runs & Automation (3 stories)

Pre-market automated analysis pipeline.

| Story | Title | Description |
|-------|-------|-------------|
| 12.1 | Cron-Based Pre-Market Trigger | Schedule analysis runs via system cron or Python scheduler. Configurable run time (default 08:00 ET). Uses watchlist from config. |
| 12.2 | Multi-Ticker Pipeline Orchestration | Run analysis across all watchlist tickers sequentially. Each ticker produces a TradeRecommendation. Progress visible via SSE. |
| 12.3 | Stale Recommendation Handling | Re-validate recommendations at market open. If market conditions shifted significantly, flag stale recommendations. valid_until countdown already implemented. |

**FRs covered:** FR32 (schedule), FR33 (manual trigger, enhanced), new FR52-FR54

### Epic 13: Enhanced Performance & Feedback Loop (3 stories)

Signal quality tracking and self-improving feedback.

| Story | Title | Description |
|-------|-------|-------------|
| 13.1 | Signal Postmortem Service | Record and classify outcomes per signal source: TRUE_POSITIVE, FALSE_POSITIVE, MISSED_OPPORTUNITY, REGIME_MISMATCH. Aggregate stats by agent, strategy, time period. |
| 13.2 | Agent Accuracy Dashboard | Track each agent's signal accuracy against trade outcomes. Show which agents contributed most to wins vs losses. Weekly agent performance table in Track Record. |
| 13.3 | Weight Adjustment Recommendations | Based on signal postmortem data, suggest agent weight adjustments. Display as "Suggested tuning" card in Track Record with current vs recommended weights. |

**FRs covered:** FR23-FR27 (performance, enhanced), new FR55-FR57

---

## 5. Implementation Handoff

**Scope Classification: Major** — 5 new epics, 20 new stories, PRD expansion, architecture extensions.

**Handoff Plan:**

| Step | Action | Agent |
|------|--------|-------|
| 1 | Approve this proposal | Bok (User) |
| 2 | Update PRD Phase 2 section with new FRs | `bmad-edit-prd` |
| 3 | Update Architecture with new services/components | `bmad-create-architecture` (incremental) |
| 4 | Add Epics 9-13 to epics.md | `bmad-create-epics-and-stories` |
| 5 | Run sprint planning | `bmad-sprint-planning` |
| 6 | Create and implement stories per epic | `bmad-create-story` → `bmad-dev-story` |

**Recommended epic order:**
1. **Epic 9** first (screeners) — highest immediate user value, most tangible
2. **Epic 10** second (regime detection) — enables smarter recommendations
3. **Epic 11** third (exposure management) — synthesizes regime into risk decisions
4. **Epic 12** fourth (automation) — operational improvement
5. **Epic 13** fifth (feedback loop) — self-improving system

**Dependencies:**
- Epic 10 → Epic 11 (regime detection feeds exposure management)
- Epic 11 → Epic 12 (exposure-aware risk judge needed before automation)
- All epics → Epic 13 (feedback loop requires data from running system)
- Epic 9 is independent — can start immediately

---

## 6. Success Criteria

- Screener tab offers ≥4 strategy choices with configurable parameters
- Market regime is classified and visible in the UI
- Risk judge gates recommendations based on exposure ceiling
- Pre-market automated runs produce recommendations without manual intervention
- Agent accuracy tracked over rolling 4-week periods
