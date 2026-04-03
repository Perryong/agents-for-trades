# Feature Landscape: Paper Trading & Validation

**Domain:** Paper trade execution, interactive charting, recommendation scoring, and performance tracking layered on an existing AI multi-agent trading framework
**Researched:** 2026-04-03
**Milestone scope:** v1.2 — NEW features only; existing equity/options/screener pipeline is unchanged

---

## Table Stakes

Features users expect. Missing = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Existing Pipeline Dependency |
|---------|--------------|------------|------------------------------|
| **TradingView Lightweight Charts — candlestick view** | Any stock analysis tool surfaces a price chart; users orient themselves visually before reading agent reports | Medium | Needs historical OHLCV data — yfinance already fetched in analysis pipeline; chart reads from same data |
| **TradingView — volume bars** | Volume is co-displayed with price on every professional chart; absence feels like a regression | Low | Same OHLCV payload; volume series is a second chart pane |
| **TradingView — trade entry/exit markers** | When Alpaca executes a paper trade, its fill price must be visible on the chart as an overlay marker; otherwise "did it execute?" is unanswerable | Medium | Alpaca fill price feeds back into chart marker data; requires connecting order response to chart state |
| **Alpaca paper trading — submit equity order** | Core v1.2 requirement; auto-execute the agent's BUY/SELL decision as a simulated trade | Medium | Agent final decision JSON (already logged to `analysis_history/`) provides ticker, direction, size; Alpaca `alpaca-py` SDK submits `MarketOrderRequest` with `paper=True` |
| **Alpaca paper trading — order status display** | User must confirm whether order was accepted/filled/rejected; silent execution is untrustworthy | Low | Poll `TradingClient.get_order_by_id()` or use order event; display in frontend alongside analysis result |
| **Alpaca paper trading — separate API keys config** | Paper account uses different keys from live account; must be configurable in environment/config without code changes | Low | Add `ALPACA_PAPER_KEY`, `ALPACA_PAPER_SECRET`, `ALPACA_PAPER=true` to existing `.env` / config pattern |
| **Recommendation scoring — per-decision outcome field** | Every logged trade decision needs a place to record whether the call was correct; without it, accuracy cannot be computed | Low | Extend existing `analysis_history/TICKER/DATE.json` schema with `outcome` field (WIN/LOSS/OPEN) and `pnl_pct` |
| **Recommendation scoring — win rate calculation** | Most fundamental accuracy metric; without it the system has no feedback loop | Low | Pure Python aggregation over logged JSON files; no new infrastructure |
| **Track record dashboard — summary statistics** | Win rate, total trades, P&L, avg gain/loss are the minimum a user expects when asking "how is this system doing?" | Medium | Aggregation over `analysis_history/` JSON files; new API endpoint returns summary dict |
| **Track record dashboard — trade history table** | Chronological list of past decisions with outcome; users expect to drill into individual calls | Low | Read from existing JSON log files; format for frontend table component |

---

## Differentiators

Features that set this system apart. Not expected, but add meaningful value.

| Feature | Value Proposition | Complexity | Existing Pipeline Dependency |
|---------|-------------------|------------|------------------------------|
| **TradingView — agent signal overlay** | Annotate the chart with which agents were bullish/bearish at the decision point; turns a price chart into an explainability view | High | Requires storing per-agent signal summaries keyed to date; existing `AgentState` fields contain this already |
| **TradingView — multi-timeframe toggle** | Daily / weekly / monthly views on same chart; traders make decisions across timeframes | Medium | yfinance supports multiple interval/period combos; same OHLCV schema |
| **Alpaca paper trading — multi-leg options order** | The options pipeline already produces a complete legs builder output (strategy, strikes, sides, ratios); auto-executing the legs via Alpaca `mleg` order class closes the loop from analysis to simulated execution | High | Alpaca Level 3 paper trading supports `order_class=mleg`; maps directly to existing `OptionsLegsBuilderReport` in `AgentState`; requires new translation layer from legs JSON to Alpaca legs array |
| **Recommendation scoring — per-agent accuracy** | Track which individual agents (technical, social, news, fundamentals, volatility, flow) had the most accurate signals over time; allows disabling consistently wrong agents | High | Requires storing individual agent votes (bull/bear/hold + conviction) per decision — partially available in existing reports |
| **Recommendation scoring — confidence-calibration view** | Compare agent's stated confidence level vs actual outcome rate; a well-calibrated system should have 80%-confident calls succeed ~80% of the time | High | Requires extracting confidence scores from final decision JSON; existing `FinalDecision` schema has `confidence` field |
| **Track record dashboard — equity curve chart** | Running P&L plotted over time using paper trade fills; shows whether the system is improving or degrading over the live paper period | Medium | Aggregate filled order P&L from Alpaca paper account via `TradingClient.get_portfolio_history()`; render with Lightweight Charts |
| **Track record dashboard — per-ticker breakdown** | Show accuracy per ticker; identifies whether system performs better on familiar names vs new picks | Low | Group `analysis_history/` JSON files by ticker; pure Python aggregation |
| **Track record dashboard — options vs equity split** | Separate win rate for pure equity decisions vs options decisions; options have different success criteria (directional correct + magnitude + timing) | Medium | `analysis_history/` JSON files already record whether options pipeline ran; filter on that field |
| **Trade outcome auto-close on Alpaca** | After N days, query Alpaca paper account to compute position P&L and auto-mark the logged decision as WIN/LOSS/OPEN | Medium | Alpaca `TradingClient.get_all_positions()` returns current unrealized P&L; compare to entry fill price |

---

## Anti-Features

Features to explicitly NOT build in v1.2.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Full TradingView Advanced Charting Library** | Requires application to TradingView for private access; proprietary, requires server-side data connector, 100kB+ overhead, and bespoke build pipeline; overkill for a companion chart | Use TradingView Lightweight Charts (MIT, 35kB, OSS, no application needed) |
| **TradingView embed widget (iframe)** | Iframe widget displays TradingView's own data, not the project's yfinance data; cannot overlay agent signals or paper trade markers; no programmatic control from React | Use `lightweight-charts` npm package directly — full programmatic control |
| **Live / real-money Alpaca trading** | Real-money execution requires regulatory compliance, additional account verification, and substantially higher risk surface; not the goal of this milestone | Paper-only; separate `ALPACA_PAPER=true` flag; live path never implemented in v1.2 |
| **Custom backtesting against historical paper trades** | Backtesting deferred to v1.3+ per PROJECT.md; options backtesting has data availability issues | Accumulate paper trade history in v1.2; backtest engine is separate milestone |
| **Portfolio rebalancing / position sizing engine** | No persistent portfolio model in the system; adding one is a distinct product requiring portfolio theory implementation | Paper orders use fixed size (configurable dollar amount or share count); no dynamic position sizing |
| **Broker integration other than Alpaca** | Multiple broker integrations multiply maintenance surface; Alpaca has the best free paper trading API in the space for algorithmic use | Alpaca only for v1.2; vendor-abstract the execution interface so future brokers can be added |
| **Real-time P&L ticker / WebSocket streaming** | Existing SSE streaming covers analysis progress, not live portfolio state; adding WebSocket introduces a second real-time protocol | Poll Alpaca REST for position updates on user action; no persistent WebSocket connection needed |
| **Social comparison / leaderboard** | No multi-user architecture; each instance tracks its own paper account | Single-account track record only |
| **Natural language outcome entry ("it went up 3%")** | Fragile LLM parsing for a task that is trivially solved by fetching actual price data from yfinance | Auto-compute outcomes from price history on a scheduled basis |

---

## Feature Dependencies

```
Existing: analysis_history/TICKER/DATE.json (final decision JSON per analysis run)
  └── Recommendation scoring
        └── Outcome field added to JSON schema (WIN/LOSS/OPEN, pnl_pct)
        └── Win rate aggregation endpoint  GET /api/track-record/summary
        └── Trade history endpoint          GET /api/track-record/trades
              └── Track record dashboard — summary stats
              └── Track record dashboard — trade history table
              └── Track record dashboard — per-ticker breakdown
              └── Track record dashboard — equity curve (needs filled P&L from Alpaca)

Existing: AgentState final decision (ticker, direction, confidence)
  └── Alpaca paper trading
        └── TradingClient(paper=True)  — alpaca-py SDK
              └── MarketOrderRequest → submit_order()  (equity)
              └── Mleg OrderRequest → submit_order()   (options, maps from OptionsLegsBuilderReport)
              └── Order fill response (fill price, fill time)
                    └── Chart marker overlay (TradingView series.setMarkers())
                    └── Outcome computation (Alpaca positions API for unrealized P&L)

Existing: yfinance OHLCV data (already fetched in analysis pipeline)
  └── TradingView Lightweight Charts
        └── createChart() + addCandlestickSeries()  (React useRef + useEffect)
        └── Volume bars  (addHistogramSeries(), priceScaleId: 'volume')
        └── Trade markers overlay (series.setMarkers(), depends on Alpaca fill data)
        └── Multi-timeframe toggle (re-fetch yfinance with different interval param)

Alpaca paper account portfolio history
  └── Track record equity curve (GET /api/track-record/equity-curve)
        └── Lightweight Charts line series in track record dashboard
```

---

## MVP Recommendation

Prioritize in this order:

1. **TradingView Lightweight Charts — candlestick + volume** — Direct value, zero broker dependency, renders using data already in the pipeline. OHLCV payload is available from yfinance. Simple `useRef` + `createChart()` pattern in React. Delivers professional chart appearance immediately.

2. **Alpaca paper trading — equity order submission** — `TradingClient(paper=True)` + `MarketOrderRequest`; triggered after the full analysis pipeline completes and user confirms "Execute Paper Trade." Writes fill response back to the analysis JSON log. Foundation for everything else in the milestone.

3. **Recommendation scoring — outcome field + win rate endpoint** — Extend JSON log schema; add `GET /api/track-record/summary` returning aggregate stats. Pure Python, no new infrastructure. Enables the track record dashboard.

4. **Track record dashboard — summary stats + trade history table** — New React tab ("Track Record") reading from `/api/track-record/summary` and `/api/track-record/trades`. Uses existing table/card component patterns.

5. **TradingView — paper trade markers** — Once Alpaca fill price is available (step 2), annotate the chart. Closes the loop between execution and visualization.

Defer to follow-up phases within v1.2:

- **Options multi-leg paper order** — Alpaca mleg support is available, but the translation layer from `OptionsLegsBuilderReport` to Alpaca legs array requires careful mapping; tackle after equity orders are stable.
- **Equity curve chart** — Requires Alpaca portfolio history accumulation over time; meaningful only after several paper trades have been made.
- **Per-agent accuracy scoring** — Requires extracting individual agent votes from existing report text (not fully structured); add after core win rate works.

---

## Complexity Notes

| Feature Area | Complexity Driver | Risk |
|---|---|---|
| TradingView chart | Low-to-medium; pure frontend, well-documented OSS library, data already exists | Chart imperative API vs React declarative model requires useEffect cleanup discipline |
| Alpaca equity paper trade | Medium; SDK is straightforward but order lifecycle (submitted → filled → rejected) must be handled | Paper fills are simulated and may lag real quotes; fill price ≠ current quote in fast markets |
| Alpaca options multi-leg | High; requires mapping from existing `OptionsLegsBuilderReport` (strategy + legs dict) to Alpaca's `legs` array format with `symbol` (OCC format), `side`, `ratio_qty` | OCC option symbol format (e.g., `AAPL250117C00150000`) must be constructed from strike/expiry/type stored in existing legs output |
| Recommendation scoring | Low; pure Python aggregation over JSON files that already exist | Outcome determination timing matters — "was the call right?" is ambiguous without a defined close rule (e.g., 5-day hold period) |
| Track record dashboard | Medium; new React tab with table + stats cards; API aggregation logic in Python | Performance at scale if `analysis_history/` grows large; add simple in-memory aggregation cache |

---

## Sources

- [TradingView Lightweight Charts — Official Library Page](https://www.tradingview.com/lightweight-charts/)
- [Lightweight Charts v5 Release Notes — TradingView Blog](https://www.tradingview.com/blog/en/tradingview-lightweight-charts-version-5-50837/)
- [Lightweight Charts React Basic Tutorial](https://tradingview.github.io/lightweight-charts/tutorials/react/simple)
- [Lightweight Charts React Advanced Tutorial](https://tradingview.github.io/lightweight-charts/tutorials/react/advanced)
- [Lightweight Charts Series Types](https://tradingview.github.io/lightweight-charts/docs/series-types)
- [TradingView Widget vs Library Product Comparison](https://www.tradingview.com/charting-library-docs/latest/getting_started/product-comparison/)
- [Alpaca Paper Trading — Official Docs](https://docs.alpaca.markets/docs/paper-trading)
- [Alpaca Options Trading — Official Docs](https://docs.alpaca.markets/docs/options-trading)
- [Alpaca Multi-Leg Options Level 3 Trading — Official Docs](https://docs.alpaca.markets/docs/options-level-3-trading)
- [Alpaca Multi-Leg Level 3 in Paper Changelog](https://docs.alpaca.markets/changelog/multi-leg-level-3-options-trading-in-paper)
- [alpaca-py Python SDK — GitHub](https://github.com/alpacahq/alpaca-py)
- [alpaca-py SDK Trading Reference](https://alpaca.markets/sdks/python/trading.html)
- [Trading Performance Metrics — Babypips](https://www.babypips.com/trading/trading-performance-metrics)
- [Top 5 Metrics for Evaluating Trading Strategies — LuxAlgo](https://www.luxalgo.com/blog/top-5-metrics-for-evaluating-trading-strategies/)
- [Complete Guide to Trading Performance Tracking — TradeFundrr](https://tradefundrr.com/trading-performance-tracking/)
- [AI Trading Tool That Keeps Score — DEV Community](https://dev.to/tradehorde/we-built-an-ai-trading-tool-that-actually-keeps-score-53ap)
