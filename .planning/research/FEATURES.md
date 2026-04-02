# Feature Landscape: Stock Recommendation / Screening System

**Domain:** AI-driven stock screener layered on top of an existing multi-agent analysis pipeline
**Researched:** 2026-04-02
**Milestone scope:** v1.1 — NEW screening/recommendation features only; existing equity/options pipeline is unchanged

---

## Table Stakes

Features users expect from any screener. Missing = the system feels broken or unusable.

| Feature | Why Expected | Complexity | Existing Pipeline Dependency |
|---------|--------------|------------|------------------------------|
| Market universe pre-filter | Narrows ~8,000 US equities to ~20-50 candidates before LLM ranking; LLM ranking of thousands of tickers is cost-prohibitive | Low | Uses `get_YFin_data_online` / yfinance bulk fetch; no new data vendor needed |
| Minimum volume threshold | Liquid stocks only; below ~500K avg daily volume options are illiquid and spreads are too wide for the options pipeline downstream | Low | yfinance `info` dict exposes `averageVolume`; stdlib calculation |
| Minimum market cap filter | Avoids micro-cap/penny stocks that are noise-heavy and thin; screener results should be analyzable by the equity agents | Low | yfinance `info` dict exposes `marketCap` |
| Relative volume signal (RVol) | Core momentum signal — volume today vs 20-day average; a stock moving on 3x+ RVol is a legitimate catalyst | Low | Derive from `get_YFin_data_online` price/volume history |
| Price momentum filter (% change) | Captures stocks with recent directional move; primary reason a trader opens a screener | Low | Derive from daily close prices in existing data layer |
| Sector / industry filter | Traders think in sector themes; needed to run sector-relative screening | Low | yfinance `info` dict exposes `sector`, `industry` |
| LLM screener agent ranks candidates | Core differentiator of this system vs a raw screener; produces top 3-5 picks with rationale from filtered list | Medium | Uses existing `quick_thinking_llm` from config; same `create_*` agent factory pattern |
| Ranked output with per-pick rationale | Users must understand WHY a ticker was ranked; "black box" outputs are not actionable | Medium | LLM agent output; structured prompt engineering |
| Select-to-analyze integration | User selects a screener pick and it pre-populates the existing analysis form (ticker + date); one-click to full pipeline | Low | Frontend: populates `AnalyzeRequest.ticker`; no backend change needed |
| CLI output for screener results | CLI is an existing primary interface (Typer + Rich); screener must work from CLI, not just frontend | Low | Extend existing CLI `main.py` patterns |
| Backend endpoint for screener | Frontend needs a REST endpoint; screener must be callable from API the same way `/api/analyze` works | Medium | New FastAPI route in `api/routes.py`; new schema in `api/schemas.py` |

---

## Differentiators

Features that separate this system from commodity screeners. Not expected, but increase value.

| Feature | Value Proposition | Complexity | Existing Pipeline Dependency |
|---------|-------------------|------------|------------------------------|
| LLM-generated per-pick rationale | Explains WHICH signals drove the ranking and how they connect (e.g., "high RVol + RSI breakout + bullish sector momentum") — most screeners give raw scores without narrative | Medium | LLM agent reads signal summary dict and produces prose; grounded in retrieved data, not model memory |
| Composite signal scoring (0-100) | Normalized score aggregating volume, momentum, and fundamental signals; enables sorting and visual ranking bar | Medium | Pure Python calculation on pre-filter output; no new vendor needed |
| Confidence flag per pick | LLM marks each pick HIGH / MEDIUM / LOW confidence based on signal alignment; LOW confidence = "worth watching but weak setup" | Low | Agent output field; structured JSON prompt |
| Sector momentum context | Pre-filter identifies which sectors are running today and weights candidates from those sectors higher | Medium | Aggregate price changes across sector ETF proxies using yfinance |
| Options-readiness flag | For each screener pick, surface whether it has liquid options (volume/OI above threshold) before user clicks Analyze with options enabled; avoids expensive failed options analysis runs | Medium | Uses existing `get_yfinance_options_chain` to check chain availability |
| SSE streaming for screener progress | Pre-filter and LLM ranking can take 10-30 seconds; streaming progress prevents "is it frozen?" frustration, consistent with existing analysis UX | Medium | Reuse existing `ProgressCallbackHandler` / `EventSourceResponse` pattern from `api/progress.py` |
| Screener results in frontend tab | Dedicated "Screener" tab in the React frontend alongside the existing report tabs; results persist across analysis runs | Medium | New React component; extend `App.tsx` tab state |

---

## Anti-Features

Features to explicitly NOT build in v1.1. Each has a principled reason.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Running full analysis pipeline on all screener results automatically | LLM cost is multiplicative: 5 picks x ~20 agent calls = ~100 LLM calls per screener run; prohibitive | Let user select which pick to send to full pipeline; explicit one-at-a-time |
| Real-time / streaming market scanning (intraday tick data) | Existing pipeline is batch/on-demand; adding tick-by-tick scanning requires a streaming data vendor (Polygon, Alpaca) not in the current stack | Stick to EOD or near-EOD snapshot data via yfinance |
| Saving screener results to persistent database | Adds infrastructure (DB schema, migrations, persistence layer) with no existing DB in the project | Log to JSON files same as existing analysis history pattern in `analysis_history/` |
| Custom filter builder UI (drag-and-drop, formula editor) | High frontend complexity; screener is a decision-support tool, not a general-purpose filter platform | Expose a small fixed set of well-chosen pre-filters with sensible defaults configurable via CLI/API params |
| Backtesting screener effectiveness | Deferred to v1.2 per PROJECT.md; options backtesting has data availability issues | Accumulate logged decisions first; backtest later |
| Portfolio tracking / open position awareness | No persistent portfolio state in the system; requires broker integration | Screener recommends fresh opportunities; position tracking out of scope |
| Natural language filter input ("show me cheap growth stocks") | LLM parsing of freeform filter criteria is fragile and slow; adds a translation layer before actual filtering | Fixed pre-filter parameters with sane defaults; LLM role is ranking, not filter parsing |
| Social/news sentiment in pre-filter | Adds N API calls in the pre-filter stage (before LLM ranking); too slow for bulk candidate generation | Social/news analysis happens inside the full pipeline after user selects a pick |

---

## Feature Dependencies

```
yfinance bulk data fetch
  └── Volume pre-filter (avg volume > threshold)
  └── Market cap pre-filter (market cap > threshold)
  └── Relative volume calculation (today vol / 20d avg)
  └── Price momentum calculation (% change N-day)
  └── Sector grouping (sector field from yfinance info)

Pre-filter output (~20-50 candidates)
  └── Composite signal scoring (pure Python)
        └── LLM screener agent (reads scored candidates dict)
              └── Ranked output (top 3-5 picks + rationale + confidence)
                    └── Frontend screener tab (displays ranked list)
                    └── CLI rich table output
                    └── "Analyze this pick" button → populates AnalyzeRequest.ticker

Options-readiness check (parallel to LLM ranking)
  └── get_yfinance_options_chain (check chain availability per candidate)
        └── Boolean flag attached to each ranked pick

New API endpoint POST /api/screen
  └── ScreenRequest schema (filters as params, llm config passthrough)
  └── SSE stream for progress (reuse ProgressCallbackHandler)
  └── ScreenResult schema (list of ranked picks)
```

---

## MVP Recommendation

Prioritize in this order:

1. **Programmatic pre-filter** — volume + market cap + RVol + momentum + sector in pure Python against yfinance data; produces a ranked-by-signal candidate list without any LLM calls; delivers immediate value and is testable in isolation
2. **LLM screener agent** — single `create_screener_agent` following existing factory pattern; takes scored candidates dict, returns top 3-5 with rationale and confidence; uses `quick_thinking_llm` (not `deep_thinking_llm` — cost control)
3. **CLI output** — Rich table showing ranked picks with score, rationale, confidence; consistent with existing CLI experience
4. **Backend endpoint + SSE** — `POST /api/screen` + SSE stream; mirrors existing `POST /api/analyze` pattern closely
5. **Frontend screener tab** — New "Screener" tab with ranked card list; each card has ticker, score, confidence, rationale snippet, and "Analyze" button that pre-fills ticker in the config sidebar

Defer to a follow-up phase:
- **Options-readiness flag** — Useful but adds N options chain fetches per screener run; add after core flow is stable
- **Sector momentum context** — ETF proxy approach requires additional design; add after basic sector filter works
- **Composite score normalization** — Can start with simple rank ordering and add normalized 0-100 score later

---

## Sources

- [8 Best Stock Screeners of 2026 — Koyfin](https://www.koyfin.com/blog/best-stock-screeners/)
- [Stock Screener Key Features — Simply Wall St](https://support.simplywall.st/hc/en-us/articles/10543502387727-Stock-Screener-Key-Features-and-How-to-s)
- [Top AI-Driven Stock Screener Tools 2026](https://www.oloumbohout.com/en/2026/03/top-ai-stock-screeners-algorithmic-trading.html)
- [Best AI Stock Screeners 2026 — AlphaLog](https://alphalog.ai/blog/best-ai-stock-screeners-2026)
- [Real-Time Stock Screener: 14 Strategies — TradesViz](https://www.tradesviz.com/blog/real-time-stock-screener/watchlist-integration/)
- [Deepvue — Smart Screener ALL/ANY Logic](https://deepvue.com/screener/smart-stock-screeners-all-any-logic/)
- [Momentum Trading with MACD and RSI — yfinance Python](https://medium.com/analytics-vidhya/momentum-trading-with-macd-and-rsi-yfinance-python-e5203d2e1a8a)
- [15 Essential Volume Indicators in Python](https://datadave1.medium.com/15-essential-volume-indicators-and-using-them-in-python-5e681a9285bd)
- [AI in Investment Analysis: LLMs for Equity Stock Ratings — ACM](https://dl.acm.org/doi/10.1145/3677052.3698694)
- [LangGraph in 2026: Build Multi-Agent AI Systems — DEV Community](https://dev.to/ottoaria/langgraph-in-2026-build-multi-agent-ai-systems-that-actually-work-3h5)
