---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments: []
workflowType: 'prd'
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 0
classification:
  projectType: 'developer_tool / api_backend'
  domain: 'fintech'
  complexity: 'high'
  projectContext: 'brownfield'
---

# Product Requirements Document - agents-for-trades

**Author:** Bok
**Date:** 2026-04-14

## Executive Summary

Agents-for-trades is a multi-agent autonomous trading system that produces specific, executable options and equity recommendations for paper trading. The system synthesizes multiple analytical dimensions — fundamentals, market technicals, news sentiment, and social signals — into a single actionable trade recommendation with exact contract details (strike price, expiry, entry price). Built for a single power user, the system simulates the full decision-making process of a thorough human trader, outputting recommendations ready for direct placement in a brokerage account.

### What Makes This Special

The system employs an ensemble of specialized AI agents — each responsible for a distinct analytical domain — that feed into a risk judge. This architecture mirrors how an experienced trader evaluates a position: checking fundamentals, reading market structure, scanning news, and gauging sentiment before committing capital. The core differentiator is the comprehensive, risk-adjusted synthesis that produces a concrete trade — not a vague directional opinion, but a specific options contract you can buy.

## Project Classification

- **Project Type:** Multi-agent system (developer tool / API backend)
- **Domain:** Fintech — options trading and market analysis
- **Complexity:** High — financial domain, real-time market data, options pricing models, multi-agent orchestration
- **Project Context:** Brownfield — existing working system being improved for actionable output and profitability

## Success Criteria

### User Success

- **Win rate target: 70%** on options and equity trades measured on a weekly basis
- **Average return per trade** is positive — winning trades outweigh losing trades in both frequency and magnitude
- The system **recognizes when not to trade** — sitting out bad conditions is a valid outcome, not a failure
- Failed trades are explainable — losses occur because guardrails were hit (stop-loss, risk limits), not because of poor analysis
- The "aha moment": returning to the app after a week and seeing a 70%+ success rate with clear reasoning for every trade taken and avoided

### Business Success

- **Paper trading phase:** Consistent 70% win rate over a 4-week rolling period demonstrates system readiness
- **Live trading transition:** System proves reliable enough on paper to justify real capital deployment
- **Capital preservation:** Guardrails prevent catastrophic losses — no single trade threatens the portfolio
- **Opportunity capture:** System identifies and acts on market conditions (e.g., volatility plays in uncertain macro environments) rather than only trading in calm markets

### Technical Success

- **Pre-market readiness:** All recommendations generated and finalized before market open (9:30 AM ET)
- **Complete trade specifications:** Every recommendation includes entry price, strike price, expiry, position size, stop-loss, profit target, and exit strategy — for both options and equity trades
- **Timing execution:** Recommendations are actionable at market open, not delayed
- **Schedule-driven operation:** Runs autonomously on a defined schedule without manual intervention
- **Crash resilience:** Completed agent work is never lost — checkpoint/resume on failure

### Measurable Outcomes

- Weekly win rate >= 70% over rolling 4-week periods
- Average return per winning trade > average loss per losing trade
- Zero trades placed without complete contract specifications
- 100% of trades have defined exit criteria (profit target + stop-loss)
- System correctly identifies and avoids trading in >= 80% of adverse market conditions

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP — fix the two critical gaps (vague recommendations, broken paper trading) that prevent the existing system from being useful and measurable.

**Resource Requirements:** Solo developer (Bok), leveraging existing codebase. No cloud infrastructure needed.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Journey 1 (Morning Pre-Market) — recommendations generated with full trade specs, reviewable in frontend
- Journey 2 (System Sits Out) — system can produce no-trade decisions with reasoning

**Must-Have Capabilities:**
1. **Actionable recommendations** — every recommendation includes: ticker, direction, trade type (options/equity), strike price, expiry, entry price, stop-loss, profit target, position size
2. **Fix options data pipeline** — resolve greeks accuracy issues so strike/pricing recommendations are reliable
3. **Standardized agent output protocol** — uniform signal structure across all agents so the risk judge synthesizes consistently
4. **Working paper trading integration** — execute recommendations in paper account, track open/closed positions
5. **Basic performance tracking** — win rate and P&L per trade, viewable in frontend
6. **No-trade logic** — risk judge can output "no trade" with reasoning when conditions don't meet thresholds

**Explicitly NOT in MVP:**
- HMM regime detection (Phase 2)
- Real-time market-hours monitoring and adjustments (Phase 2)
- Live brokerage integration (Phase 3)
- Shared data layer refactor (Phase 2)
- Schedule automation (can be triggered manually for MVP)

### Phase 2 (Growth)

- HMM regime detection (start with 2-state risk-on/risk-off)
- Shared data layer — centralize data fetching, reduce redundant API calls
- Scheduled automated runs (pre-market daily)
- Real-time monitoring during market hours with recommendation adjustments
- Enhanced performance dashboard (rolling win rate, drawdown tracking, per-strategy breakdown)
- Portfolio awareness — check open positions before recommending new trades
- Volatility-specific strategies (e.g., exploiting macro-driven volatility like tariff/policy events)

### Phase 3 (Expansion)

- Live brokerage integration (transition from paper to real trading)
- Advanced HMM (3-5 state regime model)
- Self-improving agents — feedback loop from trade outcomes to agent calibration
- Expanded stock universe beyond US markets
- Portfolio-level optimization across concurrent positions
- Backtesting engine for historical validation
- Multi-asset class support beyond equities and options

### Risk Mitigation Strategy

**Technical Risks:**
- *Options data accuracy:* Fix greeks pipeline first — without accurate data, recommendations are unreliable regardless of agent quality. Validate against known option prices before trusting automated recommendations.
- *Recommendation specificity:* Start with equity trades (simpler specs) to validate the pipeline, then layer in options complexity.

**Market Risks:**
- *Stale recommendations:* For MVP, accept the pre-market-to-open gap. Phase 2 adds real-time re-validation. Include a "freshness warning" if market conditions shift significantly at open.

**Resource Risks:**
- *Solo developer scope:* MVP is intentionally narrow — two core fixes (actionable output + paper trading). Resist adding features until these two work reliably.

## User Journeys

### Journey 1: Morning Pre-Market Routine (Primary — Success Path)

**Opening Scene:** 8:30 AM ET, 30 minutes before market open. Bok opens the app. The system has already run its scheduled analysis across the watchlist.

**Rising Action:** The dashboard shows 3 recommendations — two options plays and one equity trade. Each has a complete spec: ticker, direction, strike/expiry (for options), entry price, stop-loss, profit target, and confidence score. Bok clicks into NVDA calls and sees the synthesis: fundamentals agent flagged strong earnings momentum, news agent detected positive semiconductor policy news, market analyst identified a breakout setup, social sentiment is bullish. The risk judge rated it high-confidence with defined guardrails.

**Climax:** The recommendation is precise enough that the paper trading system has already queued the order for market open. Bok reviews, confirms it matches how he'd evaluate the trade himself, and lets it execute.

**Resolution:** End of week: 5 trades taken, 4 winners, 1 loser that hit its stop-loss cleanly. 80% win rate. The system also flagged 2 days where it sat out entirely — macro uncertainty too high. Clear reasoning for every trade taken and avoided.

### Journey 2: The System Sits Out (Edge Case — Capital Protection)

**Opening Scene:** Markets in turmoil — unexpected tariff announcement overnight. Volatility spiking.

**Rising Action:** The agents run analysis. News agent flags extreme uncertainty. Market analyst sees no clear technical setups. Fundamentals unchanged but risk environment shifted dramatically. The risk judge synthesizes all inputs.

**Climax:** Zero recommendations for the day. A "no-trade report" explains: macro volatility exceeds risk thresholds, no setups meet confidence minimums, capital preservation mode active.

**Resolution:** Bok agrees — this is exactly what he would have done manually. Capital protected. Later in the week, when volatility settles, the system captures a high-conviction volatility play.

### Journey 3: System Operator (Configuration & Troubleshooting)

**Opening Scene:** After weeks of paper trading, Bok notices the system is too conservative — passing on trades that end up being winners.

**Rising Action:** Bok reviews the risk judge's decision logs. Confidence threshold is too high, filtering out medium-conviction trades with positive expected value. He adjusts risk parameters — lowering minimum confidence from 80% to 65% for small position sizes.

**Climax:** Adds new tickers to the watchlist. The system picks them up on the next scheduled run.

**Resolution:** Following week shows more trades taken with adjusted parameters. Win rate holds at 70% with more opportunities captured. The tuning loop that makes the system better over time.

### Journey 4: Paper to Live Transition (Vision — Future Path)

**Opening Scene:** After 8 weeks of paper trading. Win rate: 72%. Average winner exceeds average loser by 2:1. Maximum drawdown within guardrails.

**Rising Action:** Bok connects his live brokerage. Configures the system to mirror paper trades with real orders at reduced position sizes. Dual execution: paper and live simultaneously.

**Climax:** First live week completes. Results track paper performance closely. System handled a partial fill gracefully.

**Resolution:** Bok gradually increases position sizes as confidence builds. The system trades the way he would — faster, more disciplined, without emotional bias.

### Journey Requirements Summary

| Journey | Capabilities Revealed |
|---------|----------------------|
| Morning Pre-Market | Scheduled analysis, complete trade specs, recommendation dashboard, agent synthesis view, paper trade auto-execution |
| System Sits Out | No-trade reporting, confidence thresholds, capital preservation logic, macro risk detection |
| System Operator | Risk parameter configuration, watchlist management, decision logs, performance tuning |
| Paper to Live | Live brokerage integration, dual-account execution, position sizing controls, performance tracking over time |

## Domain-Specific Requirements

### Known Domain Constraints

- **Options data accuracy:** Greeks calculations have known issues in current implementation; pricing data approximately correct but needs validation for trade-grade accuracy
- **Data freshness is critical:** Options prices shift significantly at market open — recommendations generated pre-market must be re-evaluated and adjustable when market reopens
- **Financial risk guardrails:** To be defined in detail. Reference: [MoneyControl — Regulations and Guardrails in Option Trading](https://www.moneycontrol.com/news/opinion/in-the-money-regulations-and-guardrails-in-option-trading-11013691.html)
- **Brokerage integration:** Provider under consideration; API constraints (rate limits, order types, PDT rules) to be evaluated when selected

### Deferred Items

- Detailed compliance and regulatory requirements for live trading
- Specific brokerage API technical constraints
- Comprehensive risk guardrail definitions (position sizing, exposure limits, margin requirements, circuit breakers)

## Innovation & Novel Patterns

### Detected Innovation Areas

1. **Multi-agent ensemble trading architecture** — Specialized AI agents (fundamentals, news, market, social) synthesized through a risk judge, mirroring institutional trading desk workflows. The innovation is in the orchestration and synthesis, not the individual components.

2. **HMM-based market regime detection as risk filter** — A Hidden Markov Model layer classifying the current market regime (bull, bear, volatile, mean-reverting) and feeding a concise regime signal to the risk judge. Contextualizes all agent recommendations — the same bullish signal means different things in different regimes, directly improving trade selection accuracy.

3. **Autonomous trade-or-no-trade judgment** — The system knows when to sit out entirely, combining regime awareness with agent confidence scoring to preserve capital.

### Market Context & Competitive Landscape

- Individual components (sentiment analysis, technical analysis, options screening) exist in many tools
- HMMs are used in quantitative finance for regime detection but rarely combined with LLM-based multi-agent systems
- No widely available retail tool combines multi-agent LLM analysis with statistical regime detection for options trading
- The combination of qualitative (LLM agents) and quantitative (HMM) approaches is the core differentiator

### Validation Approach

- Start with a simple 2-state HMM (risk-on vs. risk-off) to validate the concept
- Compare win rates with and without HMM regime filtering on paper trades
- Gradually increase regime granularity (2-state → 3-state → 5-state) based on measurable improvement
- Backtest regime classifications against historical market periods to verify accuracy

### Innovation Risk Mitigation

- **HMM complexity risk:** Start simple (2-state), add complexity only when validated
- **Regime misclassification:** Include confidence scores — risk judge can weight the regime signal based on HMM certainty
- **Overfitting:** Validate on out-of-sample data; regimes should be interpretable, not black-box
- **Integration risk:** HMM output is a single concise signal, not raw data — minimal risk of overloading the risk judge
- See also: [Risk Mitigation Strategy](#risk-mitigation-strategy) for broader technical and market risks

## Technical Architecture Requirements

### Project-Type Overview

A hybrid multi-agent system combining a Python backend (agent pipeline, data fetching, trade execution) with a React/TypeScript frontend (recommendation dashboard, charting, configuration, performance tracking). Runs locally on a daily schedule, producing pre-market recommendations that can be monitored and adjusted during market hours.

### Standardized Agent Protocol

Every agent (fundamentals, news, market, social, HMM regime detector, future agents) must output a consistent structure:
- Signal direction (bullish / bearish / neutral)
- Confidence score (0-100)
- Time horizon (intraday, swing, position)
- Supporting evidence (key data points driving the signal)
- Data freshness timestamp

This enables plug-and-play agent addition without modifying the risk judge. The risk judge consumes a uniform array of agent signals regardless of how many agents are in the pipeline.

### Shared Data Layer

- Centralize market data fetching through the existing `yfinance_cache.py` pattern
- All agents read from the same cached data snapshot, ensuring consistency
- Reduces redundant API calls and rate limit pressure
- Cache invalidation: pre-market data refreshed on schedule, intraday data refreshed at configurable intervals

### Agent-to-Frontend Communication

- Backend exposes API endpoints that the React frontend consumes
- Recommendation state (pending, active, closed) flows from backend to frontend
- Configuration changes (watchlist, risk params) flow from frontend to backend

### Configuration Surface

All configurable without code changes:
- **Watchlist** — tickers to analyze
- **Risk parameters** — stop-loss thresholds, position sizing limits, maximum portfolio exposure
- **Agent weights** — relative importance of each agent's signal in the risk judge synthesis
- **Schedule timing** — when pre-market analysis runs, monitoring intervals during market hours
- **Confidence thresholds** — minimum confidence required to generate a recommendation

### Implementation Considerations

- **Local deployment** — runs on Bok's machine, no cloud infrastructure for MVP
- **Daily schedule** — pre-market analysis triggered on schedule, execution conditional on existing portfolio state
- **Portfolio awareness** — system must know current open positions before recommending new trades to avoid overexposure
- **Frontend already exists** — React/TypeScript with charting, screener, trade sidebar, scoring, and config capabilities. New features extend the existing frontend

## Functional Requirements

### Market Analysis & Signal Generation

- FR1: System can run fundamental analysis on a given ticker and produce a structured signal (direction, confidence, evidence, time horizon)
- FR2: System can fetch and analyze recent news for a given ticker and produce a structured signal
- FR3: System can perform technical/market analysis on a given ticker and produce a structured signal
- FR4: System can analyze social media sentiment for a given ticker and produce a structured signal
- FR5: System can fetch accurate options chain data including greeks for a given ticker
- FR6: System can price options contracts accurately using current market data
- FR7: Every agent outputs signals in the standardized agent protocol format (direction, confidence 0-100, time horizon, evidence, data freshness timestamp)

### Trade Recommendation Engine

- FR8: Risk judge can synthesize signals from all agents into a single trade recommendation
- FR9: Risk judge can produce a "no trade" decision with documented reasoning when conditions don't meet thresholds
- FR10: System can generate complete trade specifications for equity trades (ticker, direction, entry price, stop-loss, profit target, position size)
- FR11: System can generate complete trade specifications for options trades (ticker, direction, strike price, expiry, entry price, stop-loss, profit target, position size)
- FR12: System can select an appropriate trading strategy (calls, puts, spreads, equity) based on market conditions
- FR13: System can assess confidence level for each recommendation and assign a confidence score

### Risk Management & Guardrails

- FR14: System can enforce stop-loss levels on every recommendation
- FR15: System can enforce position sizing limits relative to portfolio size
- FR16: System can detect adverse market conditions and suppress trading
- FR17: System can define and enforce maximum portfolio exposure limits
- FR18: System can produce capital preservation decisions when risk thresholds are exceeded

### Paper Trading & Execution

- FR19: System can submit trade orders to a paper trading account
- FR20: System can track open positions in the paper trading account
- FR21: System can close positions based on stop-loss or profit target triggers
- FR22: System can record the outcome of each trade (win/loss, P&L, reason for exit)

### Performance Tracking

- FR23: User can view win rate over a configurable time period
- FR24: User can view P&L per trade and cumulative P&L
- FR25: User can view a weekly performance summary
- FR26: User can see reasoning for each trade taken and each trade avoided
- FR27: System can calculate rolling win rate over a 4-week period

### Configuration & Control

- FR28: User can manage a watchlist of tickers to analyze
- FR29: User can configure risk parameters (stop-loss thresholds, position sizing, max exposure)
- FR30: User can configure confidence thresholds for recommendation generation
- FR31: User can adjust agent weights in the risk judge synthesis
- FR32: User can configure schedule timing for analysis runs
- FR33: User can trigger an analysis run manually

### Frontend Dashboard

- FR34: User can view pending recommendations with full trade specifications
- FR35: User can view agent-by-agent analysis breakdown for each recommendation
- FR36: User can view active and closed positions from paper trading
- FR37: User can view performance metrics and track record
- FR38: User can access and modify configuration settings from the UI

## Non-Functional Requirements

### Performance

- Full analysis pipeline for a single ticker completes within 20 minutes end-to-end
- Token usage per analysis run tracked and optimized — minimize redundant LLM calls
- Recommendations generated and available before market open (9:30 AM ET)
- Frontend renders recommendation data within 2 seconds of request
- Options chain data fresh within 15 minutes of recommendation generation

### Reliability & Crash Recovery

- Analysis pipeline supports checkpoint/resume — completed agent steps are not re-run after a crash
- Each agent's output persisted immediately upon completion, not held only in memory
- Failed agent runs retryable independently without affecting other completed agents
- System logs clear error states so the user can identify what failed and why
- No single agent failure prevents other agents from completing their analysis

### Security

- Brokerage API credentials stored securely (not in plaintext config files)
- API keys for market data and LLM providers managed through environment variables or a secrets manager
- Paper trading account access authenticated
- No sensitive credentials committed to version control

### Integration

- System handles yfinance API rate limits with exponential backoff (up to 3 retries) without crashing
- System handles LLM API rate limits and token quotas without losing completed agent progress
- Options chain data validated for completeness before agents consume it (prevent analysis on stale/missing greeks)
- Frontend-to-backend communication handles connection drops without data loss

### Cost Efficiency

- LLM token usage per analysis run measurable and reportable
- Intermediate results cached to avoid redundant API calls across agents analyzing the same ticker
- Agent prompts optimized to minimize token consumption without sacrificing analysis quality
- Cost-per-recommendation reportable so profitability can be assessed net of operational costs
