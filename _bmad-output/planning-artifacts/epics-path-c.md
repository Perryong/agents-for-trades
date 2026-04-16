---
stepsCompleted: [1, 2, 3, 4]
status: 'complete'
completedAt: '2026-04-16'
inputDocuments: ['prd.md', 'architecture.md', 'ux-design-specification.md', 'wiki/app-notes/improve-volatility-analyst.md', 'wiki/app-notes/iv-spread-skew-signals.md', 'wiki/app-notes/earnings-screener-enhancement.md', 'wiki/app-notes/rl-hedging-for-greeks-monitor.md', 'wiki/strategies/fade-retail-earnings-options.md', 'wiki/app-notes/tradingagents-paper-alignment.md']
---

# Path C: Options Overhaul + Feedback Loop — Epic Breakdown

## Overview

This document provides the epic and story breakdown for Path C of agents-for-trades, covering the full options system overhaul and feedback loop. Derived from 7 academic research papers (ingested into wiki knowledge base) and comparison with claude-trading-skills repo. Builds on completed Epics 1-12 and partially-completed Epic 13.

## Requirements Inventory

### Functional Requirements

- FR-OPT1: System can compute microstructure features (Range Volatility, Roll Measure, Price Impact, Price Dispersion) from daily OHLC data for any ticker
- FR-OPT2: Volatility analyst uses OLS regression on microstructure features to forecast near-term volatility, supplementing LLM-based assessment
- FR-OPT3: System can compute implied borrow fee from ATM put-call IV spread and flag high-fee stocks (>1% annual)
- FR-OPT4: Options flow analyst discounts IV spread/skew signals for high-borrow-fee stocks instead of interpreting them as informed trading
- FR-OPT5: System can compute Expected Announcement Volatility (AbnormalIV) for upcoming earnings
- FR-OPT6: System can compute MAX_EA (historical max earnings move) as a simpler EAV proxy
- FR-OPT7: Earnings screener surfaces high-EAV events with recommended action (sell premium / neutral / avoid buying)
- FR-OPT8: System can generate premium-selling strategy specs (short straddle, iron condor) for high-EAV earnings with defined risk
- FR-OPT9: Options chain data is usable pre-market by caching last session's snapshot with extended TTL
- FR-OPT10: System tracks thesis lifecycle (IDEA -> ENTRY_READY -> ACTIVE -> CLOSED) with per-agent signals at entry
- FR-OPT11: Postmortem service classifies trade outcomes (TRUE_POSITIVE, FALSE_POSITIVE, MISSED_OPPORTUNITY, REGIME_MISMATCH) linking to thesis
- FR-OPT12: Agent accuracy computed from thesis postmortems — per-agent signal direction vs trade outcome
- FR-OPT13: Weight adjustment recommendations generated from accuracy data with one-click apply

### Non-Functional Requirements

Existing NFR1-NFR20 from the original PRD remain applicable. No new NFRs for Path C.

### Additional Requirements

- AR-W1: Borrow fee computation must work with standard yfinance options chain data (no premium vendor needed)
- AR-W2: Microstructure features must be computable from daily OHLC only (no tick data)
- AR-W3: OLS model preferred over neural network for volatility prediction per Aldridge & Jiang finding
- AR-W4: Thesis lifecycle must integrate with existing Prediction + Trade DB models
- AR-W5: Pre-market options data cache TTL configurable (currently hardcoded 12h)

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR-OPT1 | Epic 14 | Microstructure feature computation |
| FR-OPT2 | Epic 14 | OLS volatility forecasting |
| FR-OPT3 | Epic 15 | Implied borrow fee computation |
| FR-OPT4 | Epic 15 | IV spread/skew signal reinterpretation |
| FR-OPT5 | Epic 16 | AbnormalIV computation |
| FR-OPT6 | Epic 16 | MAX_EA historical proxy |
| FR-OPT7 | Epic 16 | High-EAV event surfacing |
| FR-OPT8 | Epic 16 | Premium-selling strategy generation |
| FR-OPT9 | Epic 17 | Pre-market options data caching |
| FR-OPT10 | Epic 18 | Thesis lifecycle tracking |
| FR-OPT11 | Epic 18 | Postmortem classification |
| FR-OPT12 | Epic 19 | Agent accuracy computation |
| FR-OPT13 | Epic 19 | Weight adjustment recommendations |

## Epic List

### Epic 15: Borrow Fee Awareness & Signal Reinterpretation
The options flow analyst computes implied borrow fees from ATM put-call IV spread, flags hard-to-borrow stocks, and discounts IV spread/skew signals — preventing false bearish signals driven by borrow costs.

**User outcome:** Fewer false positives in options flow signals. System warns when short-biased strategies face hidden friction costs.
**FRs covered:** FR-OPT3, FR-OPT4
**Additional:** AR-W1

### Epic 14: Microstructure-Enhanced Volatility Forecasting
The volatility analyst produces quantitative volatility forecasts using microstructure features computed from daily OHLC, supplementing LLM-based analysis with an OLS regression model.

**User outcome:** Better volatility predictions that improve options strategy selection and pricing accuracy.
**FRs covered:** FR-OPT1, FR-OPT2
**Additional:** AR-W2, AR-W3

### Epic 16: Earnings Volatility Edge Detection
The earnings screener computes EAV metrics, surfaces high-EAV events where retail overpays, and generates premium-selling strategy specs with defined risk.

**User outcome:** Bok can identify highest-edge earnings events pre-market and act on contrarian volatility-selling strategies backed by academic evidence.
**FRs covered:** FR-OPT5, FR-OPT6, FR-OPT7, FR-OPT8

### Epic 17: Pre-Market Options Data Reliability
Options chain data is reliably available for pre-market analysis by caching the last session's snapshot with configurable TTL and providing clear degradation signals.

**User outcome:** System produces reliable options analysis at 8 AM regardless of market hours.
**FRs covered:** FR-OPT9
**Additional:** AR-W5

### Epic 18: Thesis Lifecycle & Trade Journal
Every recommendation is tracked as a thesis through its full lifecycle, storing per-agent signals at entry and linking to trade outcomes at exit. Postmortem classification runs automatically. System-wide — covers both equity and options.

**User outcome:** Full history of every trade idea from agent signals through execution to outcome, with automatic lessons-learned classification.
**FRs covered:** FR-OPT10, FR-OPT11
**Additional:** AR-W4

### Epic 19: Agent Accuracy & Self-Tuning
Agent-level accuracy computed from thesis postmortems. System generates weight adjustment recommendations with one-click apply, closing the feedback loop.

**User outcome:** Bok can see which agents are most reliable, and the system suggests how to re-weight them for better performance.
**FRs covered:** FR-OPT12, FR-OPT13

---

## Epic 15: Borrow Fee Awareness & Signal Reinterpretation

The options flow analyst computes implied borrow fees from ATM put-call IV spread, flags hard-to-borrow stocks, and discounts IV spread/skew signals — preventing false bearish signals driven by borrow costs rather than informed trading.

### Story 15.1: Compute Implied Borrow Fee from Options Chain

As a trader,
I want the system to compute the implied stock borrow fee from ATM options data,
So that I know when a stock is expensive to short and can assess the true cost of bearish strategies.

**Acceptance Criteria:**

**Given** an options chain is available for a ticker with ATM puts and calls at ~30-day expiry
**When** the borrow fee computation runs
**Then** the implied borrow fee is calculated as: `h_implied = -(sigma_C - sigma_P) / sqrt(2 * pi * (T-t))` where sigma_C and sigma_P are ATM call and put IVs
**And** the result is expressed as an annualized percentage
**And** stocks with borrow fee > 1% annual are flagged as "high-fee"
**And** stocks with borrow fee > 0.5% are flagged as "moderate-fee"
**And** the computation works with yfinance options chain data (no premium vendor required)
**And** when ATM options are unavailable or IV data is missing, the function returns `None` with a warning log
**And** unit tests verify the calculation against known examples (e.g., Tesla with high borrow fee)

### Story 15.2: Integrate Borrow Fee Filter into Options Flow Analyst

As a trader,
I want the options flow analyst to discount IV spread/skew signals for high-borrow-fee stocks,
So that I don't receive false bearish signals on stocks that are simply expensive to short.

**Acceptance Criteria:**

**Given** the implied borrow fee has been computed for a ticker (from Story 15.1)
**When** the options flow analyst evaluates IV spread and skew signals
**Then** for high-fee stocks (>1%): IV spread signal weight is reduced to 0.1 (90% discount)
**And** for moderate-fee stocks (0.5-1%): IV spread signal weight is reduced to 0.5 (50% discount)
**And** for low-fee stocks (<0.5%): IV spread signal weight is 0.8 (slight discount per research finding that even low-fee signals have marginal predictability)
**And** the borrow fee and discount applied are included in the flow analyst's output report for auditability
**And** a "Hard-to-Borrow Warning" appears in the report when borrow fee exceeds 1%
**And** the risk manager receives the borrow fee as an additional input for short-biased strategy assessment
**And** existing tests are updated and all pass

---

## Epic 14: Microstructure-Enhanced Volatility Forecasting

The volatility analyst produces quantitative volatility forecasts using microstructure features computed from daily OHLC, supplementing LLM-based analysis with an OLS regression model.

### Story 14.1: Compute Microstructure Features from Daily OHLC

As a trader,
I want the system to compute four microstructure variables from daily price data for any ticker,
So that the volatility analyst has quantitative inputs that capture market structure effects invisible to standard indicators.

**Acceptance Criteria:**

**Given** daily OHLC + Volume data is available for a ticker (at least 20 trading days)
**When** the microstructure feature computation runs
**Then** it produces four variables:
- **Range Volatility**: `(High - Low) / Open` — single-day volatility proxy
- **Roll Measure**: `2 * sqrt(-cov(Delta_P_t, Delta_P_{t-1}))` — bid-ask spread proxy from consecutive price changes (returns 0 if covariance is positive)
- **Price Impact**: `(1/T) * sum(|Delta_P| / V)` — price sensitivity to order flow
- **Price Dispersion**: `sqrt(sum(w_t * (P_t - EP_t)^2))` — volume-weighted intraday price variability (approximated from OHLC range and volume when tick data is unavailable)
**And** all features are computed from daily OHLC data only (no tick data required, per AR-W2)
**And** the function is located at `tradingagents/services/microstructure.py`
**And** features are returned as a dataclass with `ticker`, `date`, and the four float values
**And** NaN/missing data is handled gracefully (returns None for individual features when insufficient data)
**And** unit tests verify computation against hand-calculated examples

### Story 14.2: OLS Volatility Forecast Model

As a trader,
I want a simple OLS regression model that forecasts near-term volatility from microstructure features,
So that the system has a quantitative volatility prediction that complements the LLM-based assessment.

**Acceptance Criteria:**

**Given** microstructure features are available for a ticker over a rolling window (minimum 60 trading days)
**When** the OLS forecast model runs
**Then** it fits a linear regression: `RealizedVol_t+1 = alpha + beta_1*RangeVol + beta_2*RollMeasure + beta_3*PriceImpact + beta_4*PriceDispersion + epsilon`
**And** the model uses `scipy.stats.linregress` or `sklearn.linear_model.LinearRegression` (OLS, not neural networks, per AR-W3)
**And** the rolling estimation window is configurable (default 60 trading days)
**And** the output includes: predicted volatility, R-squared, and per-feature coefficients
**And** when insufficient data exists (<60 days), the model returns None with a log message
**And** the model is located at `tradingagents/services/microstructure.py` alongside the feature computation
**And** unit tests verify regression output on synthetic data with known coefficients

### Story 14.3: Integrate Microstructure Forecast into Volatility Analyst

As a trader,
I want the volatility analyst to include the OLS microstructure forecast alongside its LLM-based assessment,
So that I see both quantitative and qualitative volatility perspectives in the analysis report.

**Acceptance Criteria:**

**Given** the OLS microstructure forecast is available for a ticker (from Story 14.2)
**When** the volatility analyst agent runs its analysis
**Then** the microstructure forecast is appended to the vol context narrative as a quantitative section: "Microstructure Forecast: predicted RV = X%, R-squared = Y, dominant factor: Z"
**And** when the OLS forecast diverges from the LLM's IV-based assessment by more than 20%, a "Volatility Divergence" flag is included in the report
**And** the microstructure features (Range Vol, Roll Measure, Price Impact, Price Dispersion) are displayed in the vol context banner on the frontend
**And** when the microstructure model returns None (insufficient data), the analyst proceeds with LLM-only assessment without error
**And** the vol_context state field includes the microstructure data for downstream consumption by the risk manager
**And** existing volatility analyst tests are updated and all pass

---

## Epic 16: Earnings Volatility Edge Detection

The earnings screener computes EAV metrics, surfaces high-EAV events where retail overpays, and generates premium-selling strategy specs with defined risk.

### Story 16.1: Compute AbnormalIV and MAX_EA Metrics

As a trader,
I want the system to compute Expected Announcement Volatility metrics for any ticker with upcoming earnings,
So that I can identify which earnings events have the fattest option premiums relative to likely moves.

**Acceptance Criteria:**

**Given** a ticker has an upcoming earnings announcement and options chain data is available
**When** the EAV computation runs
**Then** AbnormalIV is calculated as: `(IV_30 - IV_60) / (1/30 - 1/60)` using ATM implied variances at ~30-day and ~60-day expirations
**And** MAX_EA is calculated as: `max(|return_i|)` for the last 20 quarterly earnings announcements using historical price data
**And** both metrics are returned alongside the earnings date and ticker
**And** when only one expiration is available (can't compute AbnormalIV), MAX_EA is used as the sole proxy
**And** when historical earnings dates are unavailable for MAX_EA, the function returns None for that metric with a warning
**And** the computation works entirely with yfinance data (options chains + historical prices)
**And** unit tests verify both metrics against hand-calculated examples

### Story 16.2: Rank and Surface High-EAV Earnings Events

As a trader,
I want the earnings screener to rank upcoming earnings by EAV and flag the top quintile as high-edge opportunities,
So that I focus my pre-market attention on the events where retail mispricing is most extreme.

**Acceptance Criteria:**

**Given** EAV metrics have been computed for multiple tickers with upcoming earnings (from Story 16.1)
**When** the earnings screener strategy runs with EAV mode enabled
**Then** all upcoming earnings within the next 14 days are ranked by AbnormalIV descending
**And** the top 20% are flagged as "High-EAV" with recommended action: "Consider selling premium"
**And** the bottom 20% are flagged as "Low-EAV" with recommended action: "Neutral — limited edge"
**And** each pick includes: ticker, earnings date, AbnormalIV, MAX_EA, EAV quintile rank, and media coverage indicator (news article count if available)
**And** a warning is displayed: "Avoid buying options before high-EAV earnings — retail overpays by 10-14% on average [Source: losing_optional.pdf]"
**And** the strategy is registered in the screener registry as "earnings-eav" alongside the existing "earnings" momentum strategy
**And** the Screener tab UI shows EAV-specific columns when this strategy is selected
**And** tests verify ranking, quintile assignment, and edge-case handling (zero candidates, single candidate)

### Story 16.3: Generate Premium-Selling Strategy Specs for High-EAV Events

As a trader,
I want the system to produce actionable premium-selling trade specs for high-EAV earnings events,
So that I can execute contrarian volatility-selling strategies with defined risk parameters.

**Acceptance Criteria:**

**Given** a high-EAV earnings event has been identified (from Story 16.2) and the ticker has liquid ATM options
**When** the strategy spec generator runs
**Then** it produces one of two defined-risk structures:
- **Iron Condor** (preferred): short ATM straddle + protective wings, with max loss defined by wing width
- **Short Straddle** (if wings are illiquid): short ATM call + short ATM put, with explicit max-loss warning
**And** the spec includes: all leg details (strike, expiry, direction, quantity), net credit received, max profit, max loss, breakeven points
**And** entry timing is 3-5 days before earnings (per research finding that retail buying peaks at t=-5 to t=-2)
**And** exit rule is: close immediately after earnings (t=0 or t=+1) to capture volatility crush
**And** position sizing limits each trade to 1-2% portfolio risk based on max loss of the structure
**And** a liquidity check is performed — if ATM bid-ask spread exceeds 15% of mid, the strategy is flagged as "Wide Spread — execution risk" rather than rejected
**And** the trade spec follows the existing `TradeSpec` protocol with `trade_type: "option"` so it integrates with the approve-to-execute flow
**And** tests verify iron condor construction, short straddle fallback, and liquidity check behavior

---

## Epic 17: Pre-Market Options Data Reliability

Options chain data is reliably available for pre-market analysis by caching the last session's snapshot with configurable TTL and providing clear degradation signals.

### Story 17.1: Fix Import-Time Cache TTL and Make It Configurable

As a trader,
I want the options data cache TTL to adapt dynamically to market hours and be configurable,
So that pre-market analysis uses cached data reliably without stale-on-restart bugs.

**Acceptance Criteria:**

**Given** the options data module at `tradingagents/dataflows/y_finance_options.py` currently evaluates `_is_market_hours()` once at import time
**When** the cache TTL is requested for any options data fetch
**Then** `_is_market_hours()` is called at fetch time (not import time), returning the correct TTL for the current moment
**And** the default TTLs are: 30 minutes during market hours (9:30-16:00 ET, weekdays), 12 hours outside market hours for options chains, 24 hours outside market hours for historical IV
**And** TTL values are configurable via the config API (`options_chain_cache_ttl_market`, `options_chain_cache_ttl_offhours`) with sensible defaults
**And** the config key allowlist in `api/config_routes.py` is updated to include the new TTL keys
**And** a restart during off-hours correctly uses the off-hours TTL (not the market-hours TTL)
**And** unit tests verify: TTL returns correct values for market hours, off-hours, weekends; restart behavior with mocked time

### Story 17.2: Data Quality Validation and Degradation Signals

As a trader,
I want the system to validate options data quality before analysis and clearly signal when data is degraded,
So that I know whether to trust the options recommendations or wait for fresh data at market open.

**Acceptance Criteria:**

**Given** options chain data has been fetched (from cache or live) for a ticker
**When** the data quality check runs before any analyst consumes the data
**Then** it validates: IV values are non-zero for ATM options, at least 3 expiration dates exist, bid-ask spreads are present (non-zero), Greeks are calculable from the available IV + last price
**And** a data quality score is assigned: "Fresh" (fetched <30 min ago during market hours), "Cached" (last session data, off-hours), "Stale" (>24h old), "Degraded" (missing critical fields)
**And** "Cached" data is acceptable for pre-market analysis with a note: "Using last session close data — verify at open"
**And** "Stale" data triggers a warning in the vol context banner: "Options data >24h old — results may be unreliable"
**And** "Degraded" data causes the options pipeline to return a "DATA_UNAVAILABLE" result rather than producing unreliable recommendations
**And** the data quality label is propagated to the frontend via the analysis SSE stream and visible in the recommendation card
**And** tests verify all four quality states with fixture data

---

## Epic 18: Thesis Lifecycle & Trade Journal

Every recommendation is tracked as a thesis through its full lifecycle, storing per-agent signals at entry and linking to trade outcomes at exit. Postmortem classification runs automatically. System-wide — covers both equity and options.

### Story 18.1: Thesis Data Model and Lifecycle State Machine

As a trader,
I want every analysis result tracked as a thesis with a defined lifecycle,
So that I can follow any trade idea from inception through execution to outcome in a single record.

**Acceptance Criteria:**

**Given** the database has existing Prediction and Trade models
**When** the Thesis model is created
**Then** a `theses` table is added to `api/models.py` with fields: `id` (PK), `ticker` (string, indexed), `direction` (string), `trade_type` (string: "equity" | "option"), `status` (string), `confidence_at_entry` (float), `agent_signals_json` (text — snapshot of all agent signals at thesis creation), `entry_price` (float, nullable), `stop_loss` (float, nullable), `target_price` (float, nullable), `strategy_name` (string, nullable), `prediction_id` (FK to Prediction, nullable), `trade_id` (FK to Trade, nullable), `created_at` (datetime), `updated_at` (datetime), `closed_at` (datetime, nullable), `close_reason` (string, nullable)
**And** the status field follows a state machine: `IDEA` -> `ENTRY_READY` -> `ACTIVE` -> `CLOSED` (also `INVALIDATED` from any state)
**And** invalid state transitions are rejected (e.g., CLOSED -> IDEA)
**And** a DB migration function (`ensure_theses_table`) is added and called on app startup
**And** the `agent_signals_json` stores the full signal dict from every agent that participated in the analysis (name, direction, confidence, evidence)
**And** `prediction_id` links back to the Prediction record and `trade_id` links to the Trade record when a paper trade is executed
**And** unit tests verify state transitions, invalid transition rejection, and FK relationships

### Story 18.2: Auto-Create Thesis on Analysis Completion

As a trader,
I want a thesis record created automatically when analysis completes,
So that every analysis is tracked without manual intervention.

**Acceptance Criteria:**

**Given** an analysis run completes and Prediction records are written (existing flow in `api/routes.py`)
**When** the prediction writing logic runs
**Then** a Thesis record is created with status `IDEA` for each Prediction
**And** `agent_signals_json` is populated from the analysis state's agent signal dicts (fundamentals_signal, news_signal, market_signal, technical_signal, social_signal — whichever are non-None)
**And** `confidence_at_entry`, `direction`, `trade_type`, `ticker`, `strategy_name`, `entry_price`, `stop_loss`, `target_price` are populated from the Prediction's trade_spec_json
**And** `prediction_id` links to the corresponding Prediction record
**And** when a recommendation is approved and a paper trade is submitted, the thesis status transitions to `ACTIVE` and `trade_id` is set to the Trade record ID
**And** when a recommendation is skipped, the thesis status transitions to `INVALIDATED` with close_reason "Skipped by user"
**And** existing approve/skip flows in `api/recommendation_routes.py` are updated to transition thesis state
**And** tests verify thesis creation on analysis completion and state transitions on approve/skip

### Story 18.3: Auto-Close Thesis on Trade Exit and Postmortem Classification

As a trader,
I want theses automatically closed when trades exit, with the outcome classified for learning,
So that every completed trade generates a structured postmortem record without manual effort.

**Acceptance Criteria:**

**Given** an ACTIVE thesis has a linked Trade record
**When** the trade is closed (stop-loss hit, target hit, manual close, or expired)
**Then** the thesis status transitions to `CLOSED` with `closed_at` timestamp and `close_reason` from the Trade record
**And** a postmortem classification is computed and written to the `signal_postmortems` table (existing model):
- **TRUE_POSITIVE**: majority of agent signals matched the trade outcome (e.g., agents said BUY, trade was a WIN)
- **FALSE_POSITIVE**: majority of agents were wrong (agents said BUY, trade was a LOSS)
- **MISSED_OPPORTUNITY**: thesis was INVALIDATED (skipped) but the price moved in the predicted direction by more than the target would have captured
- **REGIME_MISMATCH**: the regime at entry (from regime_detector) differs from regime at exit, suggesting the market context shifted
**And** the postmortem record includes: thesis_id, classification, agent_signals_at_entry (from thesis), actual_outcome, pnl_pct, regime_at_entry, regime_at_exit
**And** MISSED_OPPORTUNITY classification requires checking the ticker's price movement between thesis creation and a configurable lookback window (default 5 trading days)
**And** the `GET /api/postmortem/summary` endpoint returns real data (no longer empty)
**And** tests verify all four classification paths with fixture data

### Story 18.4: Thesis Dashboard in Track Record

As a trader,
I want to view all theses in the Track Record tab grouped by status and outcome,
So that I can review the full history of every trade idea and its resolution.

**Acceptance Criteria:**

**Given** thesis records exist in the database
**When** the user navigates to the Track Record tab
**Then** a "Thesis Journal" section displays theses grouped by status: ACTIVE (top), CLOSED (below), INVALIDATED (collapsed)
**And** each thesis row shows: ticker, direction, trade_type badge (Equity/Options), confidence_at_entry, entry_price, current status, P&L (if closed), close_reason, created_at
**And** expanding a thesis shows the per-agent signal snapshot (agent name, direction, confidence) and the postmortem classification if closed
**And** a `GET /api/theses` endpoint returns thesis records with optional filters: `?status=ACTIVE`, `?status=CLOSED`, `?ticker=AAPL`
**And** the endpoint supports pagination (`?limit=20&offset=0`)
**And** tests verify the API endpoint with various filter combinations

---

## Epic 19: Agent Accuracy & Self-Tuning

Agent-level accuracy computed from thesis postmortems. System generates weight adjustment recommendations with one-click apply, closing the feedback loop.

### Story 19.1: Compute Agent Accuracy from Postmortems

As a trader,
I want to see which agents are most accurate at predicting trade outcomes,
So that I can trust the right signals and understand where the system is weakest.

**Acceptance Criteria:**

**Given** closed theses with postmortem records exist in the database (from Epic 18)
**When** agent accuracy computation runs
**Then** for each agent (fundamentals, news, market, technical, social), the following metrics are computed:
- **Accuracy %**: percentage of theses where the agent's signal direction matched the trade outcome (BUY+WIN or SELL+WIN = correct)
- **Avg Confidence**: mean confidence score across all theses where this agent participated
- **True Positive Rate**: correct bullish signals / total bullish signals
- **False Positive Rate**: incorrect bullish signals / total bullish signals
- **Sample Count**: number of theses this agent participated in
**And** metrics are computed separately for equity and options theses (trade_type split)
**And** a `GET /api/agents/accuracy` endpoint returns the per-agent accuracy breakdown with optional `?period=4w` filter (default: all time)
**And** when fewer than 10 closed theses exist, a disclaimer is included: "Insufficient data for reliable accuracy metrics"
**And** the computation uses SQL aggregation (not loading all records into memory)
**And** tests verify accuracy computation with fixture data covering correct/incorrect signals across multiple agents

### Story 19.2: Agent Performance Display in Frontend

As a trader,
I want the Track Record tab to show real agent accuracy metrics instead of placeholder zeros,
So that I can see which agents contribute most to wins and which to losses.

**Acceptance Criteria:**

**Given** agent accuracy data is available from the API (from Story 19.1)
**When** the user views the Track Record tab
**Then** the `AgentPerformanceTable` component displays real data: agent name, accuracy %, avg confidence, true positive rate, false positive rate, sample count
**And** agents are sorted by accuracy descending
**And** accuracy is color-coded: green (>65%), amber (50-65%), red (<50%)
**And** a toggle switches between "All", "Equity Only", "Options Only" views
**And** when insufficient data exists, the disclaimer message is displayed instead of the table
**And** the component fetches from `GET /api/agents/accuracy` with the selected period/type filters

### Story 19.3: Weight Adjustment Recommendations

As a trader,
I want the system to suggest agent weight adjustments based on historical accuracy,
So that I can tune the risk judge to rely more on agents that have been right and less on those that have been wrong.

**Acceptance Criteria:**

**Given** agent accuracy data exists with at least 20 closed theses
**When** the weight recommendation algorithm runs
**Then** recommended weights are computed as: `new_weight = normalize(accuracy * avg_confidence)` across all agents, scaled to sum to the number of agents (so average weight remains 1.0)
**And** the algorithm accounts for regime by computing separate accuracy per regime type (Broadening, Contraction, etc.) and weighting toward the current regime's accuracy
**And** a `GET /api/agents/suggested-weights` endpoint returns: for each agent, `current_weight`, `recommended_weight`, `accuracy_basis`, `confidence_basis`, `sample_count`
**And** the response includes a `confidence_level`: "HIGH" (>50 theses), "MEDIUM" (20-50), "LOW" (<20, returns current weights unchanged)
**And** when fewer than 20 theses exist, the endpoint returns current weights with a message: "Need more trades for reliable tuning recommendations"
**And** tests verify weight computation, regime weighting, and insufficient-data fallback

### Story 19.4: One-Click Weight Apply in Frontend

As a trader,
I want to review suggested weight adjustments and apply them with one click,
So that tuning the system is effortless and I don't have to manually calculate or type values.

**Acceptance Criteria:**

**Given** suggested weights are available from the API (from Story 19.3)
**When** the user views the Track Record tab
**Then** a "Suggested Tuning" card displays below the Agent Performance table showing: agent name, current weight, recommended weight (with arrow indicating increase/decrease), accuracy basis, sample count
**And** a visual bar shows the delta between current and recommended for each agent
**And** an "Apply Suggested Weights" button is visible when confidence_level is "HIGH" or "MEDIUM"
**And** clicking "Apply" calls `PUT /api/config/agent_weight_{name}` for each agent with the recommended value
**And** a success confirmation shows: "Weights updated — changes take effect on next analysis run"
**And** when confidence_level is "LOW", the button is disabled with tooltip: "Need more trades for reliable recommendations"
**And** the card is hidden entirely when zero closed theses exist
