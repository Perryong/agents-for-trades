# Domain Pitfalls — Paper Trading, Charting, Scoring, and Track Record Dashboard

**Domain:** Adding TradingView charts, Alpaca paper trading, recommendation scoring, and track record dashboard to existing AI trading analysis system
**Researched:** 2026-04-03
**Confidence:** HIGH (Alpaca/charting), MEDIUM (scoring methodology), HIGH (integration patterns)
**Context:** v1.2 features bolt onto existing LangGraph + FastAPI + React stack with JSON trade logs.

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or features that undermine user trust in AI recommendations.

---

### Pitfall 1: lightweight-charts v5 API Incompatibility With Existing React Patterns

**What goes wrong:**
lightweight-charts v5 (released late 2024) has hard breaking changes from v4. The series creation API changed from type-specific methods (`chart.addLineSeries()`) to a unified method (`chart.addSeries(LineSeries, options)`). The watermark option was removed from `createChart` and moved to a separate plugin. The library dropped CommonJS support entirely and requires ES2020+. Community tutorial code and Stack Overflow answers are predominantly v4, so developers who copy examples from search results will get silent errors or runtime failures — the old API calls do not throw helpful errors, they just produce no output.

**Why it happens:**
Most React + TradingView tutorials in circulation were written for v3 or v4. The npm package installs v5 by default (latest). A developer follows a 2023 tutorial, installs the current package, and finds the chart renders nothing. They add `console.log` but nothing obvious fails — `createChart` succeeds, `addLineSeries` is silently undefined in v5.

**Consequences:**
- Silent rendering failure: chart container renders but is empty
- React StrictMode (which Vite projects enable by default in development) double-invokes `useEffect`, and without proper cleanup, the chart is created twice — the second instance overwrites the first without removing it, causing memory leaks detectable only in production after hours of use
- Primitives (annotations, markers) do not synchronize with chart position on scroll/resize in React — a confirmed v5.0.8 regression in React + Vite environments (GitHub issue #1920)

**How to avoid:**
- Pin exact version in `package.json`: `"lightweight-charts": "^5.0.0"` and always use the v5 migration guide
- Use the pattern from official v5 React tutorial exactly: `useRef` for container, `useEffect` for `createChart`, return `chart.remove()` as cleanup — never create a chart outside a `useEffect`
- Series creation: `import { createChart, CandlestickSeries } from 'lightweight-charts'` then `chart.addSeries(CandlestickSeries, options)`
- In React StrictMode, verify cleanup runs by checking that no duplicate chart DOM nodes exist after mount
- Do not use the community wrapper `kaktana-react-lightweight-charts` — it targets v3 and is unmaintained

**Warning signs:**
- Chart container is present in the DOM but visually empty with no console errors
- Two canvas elements visible inside chart container div (double-mount not cleaned up)
- `TypeError: chart.addLineSeries is not a function` — you have v5 with v4 code

**Phase to address:** TradingView charts integration phase, before any data wiring.

---

### Pitfall 2: Alpaca Paper vs. Live API Key Environment Mismatch

**What goes wrong:**
Alpaca uses separate API key pairs for paper trading and live trading, served from different base URLs (`https://paper-api.alpaca.markets` vs `https://api.alpaca.markets`). Using paper keys against the live endpoint returns 401. Using live keys against the paper endpoint also fails. The error message is generic — it does not say "wrong environment." Developers who store both key sets in `.env` and switch between them by editing a variable often forget to change the base URL, or vice versa.

**Why it happens:**
Single-key mental model from other services. Most APIs use the same key for staging and production, switching environments via URL only. Alpaca requires both key pair AND URL to match. The Python SDK `alpaca-py` does handle this if you pass `paper=True` to the client constructor, but if the client is initialized from raw environment variables, the guard is bypassed.

**Consequences:**
- Attempted paper orders silently fail or return permission errors that look like account setup problems
- Developer spends time debugging account status rather than the actual key/URL mismatch
- If live keys are accidentally used in a "paper trading" test, real orders may be submitted

**How to avoid:**
- Use `alpaca-py` (not the deprecated `alpaca-trade-api`) — it is the only officially supported Python SDK as of 2025
- Always initialize the `TradingClient` with explicit `paper=True`: `TradingClient(api_key=key, secret_key=secret, paper=True)`
- Store paper and live credentials in separate `.env` sections with explicit prefixes: `ALPACA_PAPER_KEY`, `ALPACA_PAPER_SECRET` — never `ALPACA_KEY` which is ambiguous
- Add a startup assertion: if `ENVIRONMENT == "paper"` and `ALPACA_BASE_URL` does not contain `paper-api`, raise a configuration error before the server starts
- Never commit `.env` with live keys; add both `.env` and `.env.live` to `.gitignore`

**Warning signs:**
- HTTP 401 despite correct-looking credentials
- HTTP 403 "insufficient permission" when account setup looks correct
- Orders appear to be submitted but never show up in the paper account dashboard

**Phase to address:** Alpaca paper trading integration phase, specifically the environment setup and client initialization step.

---

### Pitfall 3: Alpaca Options Multi-Leg Orders Are Not Fully Supported in Paper Trading

**What goes wrong:**
The system's options agents build multi-leg strategies (spreads, straddles, iron condors). The user expects these to be executable via Alpaca paper trading. However, Alpaca does not support Bracket orders or OTO (One-Triggers-Other) orders for options contracts. While Alpaca added multi-leg options support in late 2024, the `complex_order_type` support for options is still limited compared to equities. A developer who tests with simple equity bracket orders will find paper trading works fine, then hits a hard API error when submitting a multi-leg options spread.

**Why it happens:**
Options multi-leg support was added to Alpaca in stages. Documentation reflects what is planned or recently added but community forum threads reveal persistent gaps. Equity and options trading have different capability matrices in Alpaca's paper environment that are not clearly summarized in a single location.

**Consequences:**
- The most valuable part of the system (options recommendations from the 7-agent options pipeline) cannot be auto-executed via paper trading without extra leg-by-leg decomposition logic
- User discovers this limitation after the paper trading feature is already implemented and advertised as supporting the full options workflow

**How to avoid:**
- Explicitly scope paper trading execution for v1.2 to equity orders only (market and limit orders on the underlying stock)
- Document in the UI that options execution via Alpaca is single-leg only and multi-leg strategies must be submitted individually
- Design the execution layer as an abstraction so a future vendor with better options multi-leg support (Interactive Brokers, TD Ameritrade API) can be substituted
- Test each order type in paper mode before writing execution code for it

**Warning signs:**
- `422 Unprocessable Entity` or `400 Bad Request` with message about "complex orders not supported for options trading"
- Order submission succeeds for equities but fails identically for options contracts

**Phase to address:** Alpaca paper trading integration phase, requirements definition step — clarify execution scope before building.

---

### Pitfall 4: Blocking the FastAPI Event Loop With Synchronous Alpaca SDK Calls

**What goes wrong:**
The existing FastAPI backend uses `async def` route handlers and SSE streaming. The `alpaca-py` SDK's trading client methods (`submit_order`, `get_order`, `get_all_positions`) are synchronous by default. Calling them directly inside an `async def` handler blocks the event loop for the duration of the HTTP request to Alpaca's API — typically 100-500ms. During that block, no SSE events can be dispatched to the frontend, the progress stepper freezes, and other concurrent requests stall.

**Why it happens:**
Developers add `import alpaca_trade_api` or `from alpaca.trading.client import TradingClient`, call `client.submit_order(...)` inside an `async def` endpoint, and it works in local testing where no concurrent requests exist. The blocking nature is invisible under single-user conditions.

**Consequences:**
- SSE stream stalls visibly during order submission — the analysis progress stepper freezes for 100-500ms per Alpaca call
- Under concurrent analysis runs (two browser tabs), Alpaca calls from one request delay SSE delivery to the other
- If Alpaca's API is slow (timeouts), the entire FastAPI process becomes unresponsive

**How to avoid:**
- Wrap all synchronous `alpaca-py` calls with `asyncio.to_thread()`: `await asyncio.to_thread(client.submit_order, order_request)`
- Alternatively, implement a dedicated `AlpacaExecutor` class that runs on a `ThreadPoolExecutor` and exposes an `async` interface to the rest of the backend
- Never use `asyncio.run()` inside a running event loop — this is a nested event loop crash
- Test under concurrent SSE streams: open two browser tabs running analysis simultaneously; confirm SSE delivery does not stall when an order is submitted in one tab

**Warning signs:**
- SSE progress events have irregular timing gaps that correlate with order submission timing
- FastAPI access log shows request durations that include Alpaca response times
- Uvicorn warning: "Detected a call to a blocking function in a non-blocking context"

**Phase to address:** Alpaca paper trading integration phase, API client setup.

---

### Pitfall 5: Recommendation Scoring System Built Around Win Rate Alone

**What goes wrong:**
The recommendation scoring feature produces a win rate percentage as its primary headline metric (e.g., "AI recommendations: 67% win rate"). This number is prominently displayed on the track record dashboard and used as the primary indicator of system quality. The metric is mathematically incomplete and actively misleading: a 67% win rate with 0.5:1 risk-reward loses money; a 40% win rate with 3:1 risk-reward makes money. Users see a high win rate and become overconfident; users see a low win rate and dismiss a profitable system.

**Why it happens:**
Win rate is the most intuitive metric and the easiest to calculate from the existing JSON trade logs. It requires only counting `decision == "BUY"` entries where subsequent price moved up. Building a full expectancy calculation requires knowing exit prices and holding periods, which the current log schema may not capture.

**Consequences:**
- Dashboard headline metric actively misleads user about AI system quality
- A period where the system recommended many small winners (correct calls on low-conviction setups) followed by one large loss looks better in win rate than it actually was
- Expectancy-negative results can masquerade as good performance for months if only win rate is tracked

**How to avoid:**
- Primary metric must be expectancy: `(win rate × avg winner size) - (loss rate × avg loser size)`
- Display these together: win rate, average winner, average loser, profit factor (gross profit / gross loss), and expectancy — never win rate alone
- The JSON trade log schema must capture: `recommendation_direction`, `confidence_level`, `recommended_entry_price`, and `target_exit_price` — not just the decision
- Add a data disclaimer on the dashboard: "Paper trading results do not reflect real-world slippage, market impact, or execution delays"

**Warning signs:**
- Dashboard mockup shows only win/loss counts and a percentage
- The scoring schema design starts with "count wins" before defining what a win means (exit conditions, time horizon)
- Track record looks excellent in paper mode but the position sizing has never been defined

**Phase to address:** Recommendation scoring system phase, schema design step before any metrics are displayed.

---

### Pitfall 6: Paper Trading Performance Overstates Real-World Results Due to Perfect Fills

**What goes wrong:**
Alpaca paper trading fills orders at the exact bid/ask prices at the moment of submission with no slippage, no market impact, and instant execution. Real trading introduces slippage (especially on options), execution delays, and bid/ask spreads that erode edge. The track record dashboard will show paper trading results that are systematically better than what would be achieved in live trading — sometimes materially so for options strategies with wide spreads or low liquidity.

**Why it happens:**
This is an inherent limitation of paper trading simulation, not a bug. The issue is a design problem: if the track record dashboard presents paper results as a fair representation of what the AI system achieves in the market, users who transition to live trading will be disappointed and may lose confidence in the system.

**Consequences:**
- System appears to have a strong edge in paper mode; edge disappears in live trading
- Options strategies with 0.10+ wide bid/ask spreads are particularly affected — a theoretical edge of $0.08 is eliminated entirely
- If the track record is used to evaluate whether to deploy real capital, it will produce a biased recommendation

**How to avoid:**
- Display a persistent disclaimer on the track record dashboard: "Simulated performance. Paper fills assume zero slippage and instant execution. Real-world results will differ, especially for options."
- Add an adjustable slippage estimate field in the track record settings (default: $0.02/share for equities, half the spread for options)
- Track the spread at time of recommendation alongside the fill price so the dashboard can show "estimated real-world edge after spread" separately from "paper fill P&L"
- Never use paper trading P&L as a proxy for live trading P&L in any summary or headline stat

**Warning signs:**
- Track record dashboard shows no mechanism to adjust for slippage
- All paper orders show fills at exactly the mid-price
- Dashboard summary says "profit" without any disclaimer about simulation limitations

**Phase to address:** Track record dashboard phase, before any P&L display is designed.

---

### Pitfall 7: Trade Log JSON Schema Insufficient for Scoring and Track Record

**What goes wrong:**
The existing JSON trade logs record the AI's decision (`BUY`/`SELL`/`HOLD`) and the analysis date, but do not capture the information needed to score recommendation quality: the entry price at recommendation time, the target exit price or time horizon, or the actual outcome. Building a scoring system on top of logs that lack this data requires either retrofitting the schema (corrupting historical records), running a second price lookup for every past decision (expensive and error-prone for historical dates), or defining scoring criteria that don't actually measure prediction accuracy.

**Why it happens:**
The existing log format was designed for record-keeping and review, not for outcome measurement. Adding scoring requirements changes the log schema, and schema changes to historical files are destructive if not handled carefully.

**Consequences:**
- All historical decisions before v1.2 cannot be scored against the same methodology as future decisions — track record starts from zero at v1.2 launch
- If the schema is patched retroactively with price data fetched from yfinance, the historical prices may differ from what was actually available at the time (ex-dividend adjustments, splits, data corrections)
- Inconsistent schema between pre-v1.2 and post-v1.2 logs breaks any analytics query that spans the boundary

**How to avoid:**
- Define the v1.2 log schema before building any scoring feature — it must include: `ticker`, `decision_date`, `decision_direction`, `confidence_score`, `price_at_decision`, `recommended_target_price`, `recommended_stop_price`, `target_horizon_days`
- Use versioned schema with a `schema_version` field in every log entry — v1.2 logs get `"schema_version": "1.2"`
- Do not modify historical log files — store v1.2+ logs in a new file or directory, and clearly label the track record start date as the v1.2 deployment date
- The scoring system must gracefully handle missing fields (pre-v1.2 logs) and exclude them from quantitative metrics while still showing them in the history view

**Warning signs:**
- Scoring feature mockup assumes `entry_price` field exists in historical logs
- Track record dashboard shows historical decisions from before the paper trading feature was added
- Schema for the log file has not been updated in a PR before any scoring code is written

**Phase to address:** Recommendation scoring system phase, before writing any code — schema design is the critical first step.

---

## Moderate Pitfalls

---

### Pitfall 8: TradingView Chart Data and Analysis Timestamps Out of Sync

**What goes wrong:**
The chart displays OHLCV data from yfinance or Tradier. The analysis result shown alongside the chart was generated at a specific point in time. When the user views the chart after market hours, the chart shows the most recent bar at the current time while the analysis vertical line or marker points to when the analysis was run (possibly hours or days earlier). The visual relationship between the charted price action and the AI decision annotation becomes confusing, especially if the price has moved significantly since the analysis.

**Why it happens:**
Chart data is fetched fresh each time the chart component mounts. Analysis results are loaded from the JSON log at the time the analysis was run. There is no coordination between the two time series.

**How to avoid:**
- Store the exact UTC timestamp of analysis completion in the trade log: `analysis_completed_at`
- Chart component receives this timestamp and renders a vertical line at that point on the time axis with a tooltip showing "Analysis run: [timestamp]"
- If the analysis timestamp is outside the chart's current view window, show a banner: "Analysis was run outside current chart range — click to navigate to that date"
- Use the same data vendor (same price feed) for chart data and the price stored in the analysis log to avoid price discrepancies from different data sources

**Warning signs:**
- Chart shows a price of $150 and the analysis says "recommended entry: $162" with no visual explanation of the time gap
- Analysis markers on the chart are placed at the wrong bar because the log stores date-only, not datetime

**Phase to address:** TradingView charts integration phase, data alignment design.

---

### Pitfall 9: Alpaca Order State Machine Not Handled — Stale "Pending" Orders

**What goes wrong:**
When an order is submitted to Alpaca paper trading, it does not immediately become `filled`. Orders transition through states: `new` → `accepted` → `partially_filled` → `filled` (or `canceled`, `expired`, `rejected`). The backend submits an order and stores the `order_id`, but the frontend shows "Order Submitted" without ever polling for the final fill status. The track record dashboard never knows if the order was actually filled or was rejected, so all submitted orders are assumed to be executed.

**Why it happens:**
Order submission is the easy, visible step. Order status polling is an asynchronous follow-up concern that is deferred and then forgotten. The Alpaca paper environment processes orders near-instantly during market hours, so in local testing the order appears to fill immediately — the polling gap is invisible.

**Consequences:**
- Track record dashboard shows "executed" positions that were actually rejected or expired
- P&L calculations are based on imaginary fills
- If the user analyzes options orders (which have longer fill queues), the problem is visible: options orders in paper mode do not always fill instantly

**How to avoid:**
- Never mark an order as "executed" in the track record until Alpaca confirms `status == "filled"` or `status == "partially_filled"`
- Implement a lightweight polling loop: after submission, poll `GET /v2/orders/{order_id}` every 5 seconds, up to 12 times (60 seconds), then mark as `timeout` if not filled
- For market hours: orders should fill within 1-2 polls. For options or limit orders: surface the pending state in the UI explicitly
- Store the Alpaca `order_id` in the trade log so orders can be re-queried later if needed

**Warning signs:**
- Track record shows all orders as filled immediately at submission time
- No `order_id` field in the execution log schema
- No `ORDER_STATUSES` state in frontend — UI only shows "submitted" with no transition to "filled" or "failed"

**Phase to address:** Alpaca paper trading integration phase, order lifecycle management.

---

### Pitfall 10: Track Record Dashboard Using Relative Returns Without Position Sizing

**What goes wrong:**
The dashboard shows the AI's recommendations as a list of "correct" or "incorrect" calls without defining what position size was used. Two decisions — one on AAPL at 1% of portfolio and one on TSLA at 10% of portfolio — have very different impact on actual P&L but are counted equally on the track record. The win rate and even the average winner/loser metrics are distorted because they are calculated per-decision without weighting by position size.

**Why it happens:**
Position sizing is not currently part of the AI system — it makes directional calls but does not specify what percentage of capital to deploy. Without defined position sizes, a fair P&L calculation requires assuming equal-weight sizing, which is a simplification that the dashboard should make explicit.

**How to avoid:**
- All track record P&L calculations must assume a configurable fixed-dollar position size (e.g., $1,000 per recommendation as default) — make this explicit in the UI
- Display: "Assuming $[X] per recommendation. Adjust in settings." 
- Store the assumed position size alongside each execution record
- Never claim "total portfolio return" without a complete, consistent position sizing model — instead show "total P&L assuming $X per trade"

**Warning signs:**
- Dashboard shows percentage gain/loss per trade without an assumed position size
- "Total portfolio return" is displayed as a metric without a defined initial portfolio value
- Recommendations on penny stocks and large-caps are treated as equivalent without normalization

**Phase to address:** Track record dashboard phase, metrics definition.

---

### Pitfall 11: Scoring System Optimized for LLM Confidence Instead of Outcome Accuracy

**What goes wrong:**
The recommendation scoring feature measures how confident the AI's recommendation was (e.g., uses the `confidence_score` from the final decision node) as a proxy for recommendation quality. High-confidence recommendations get high scores. The system does not verify whether the high-confidence recommendations actually moved in the predicted direction. This creates a feedback loop where the scoring reinforces AI verbosity and certainty rather than accuracy.

**Why it happens:**
Confidence scores are immediately available from existing data. Outcome data requires waiting for the market to move and then doing a price lookup — it requires a deferred evaluation that runs after the recommendation date, which is architecturally more complex.

**How to avoid:**
- Score = outcome accuracy only. Confidence score is a secondary attribute that is displayed alongside the outcome, never as the primary score
- Scoring requires deferred evaluation: schedule a background job (or manual trigger) that runs N trading days after each recommendation and fetches the price, computes the actual outcome, and writes it back to the log
- The recommendation record must have two states: `pending_outcome` (within the evaluation window) and `scored` (outcome recorded)
- Surface the pending/scored distinction clearly in the dashboard — never show a score for a recommendation that has not been evaluated yet

**Warning signs:**
- Scoring job description says "use confidence score" or "AI certainty"
- Track record shows scores for recommendations made today (outcome not yet knowable)
- No deferred evaluation job or cron step is mentioned in the architecture

**Phase to address:** Recommendation scoring system phase, metrics definition step.

---

### Pitfall 12: Charts Feature Adding a Second Data Vendor Path That Diverges From Analysis

**What goes wrong:**
The chart fetches OHLCV data via a dedicated chart API endpoint that calls yfinance directly. The analysis pipeline fetches price data via the existing `VENDOR_METHODS` abstraction in `interface.py`. If the chart endpoint bypasses the vendor abstraction and goes directly to yfinance, two separate data paths exist for the same data. When the primary vendor is switched (e.g., from yfinance to Polygon), the chart endpoint still fetches from yfinance, causing the chart price history to diverge from the prices recorded in the analysis logs.

**Why it happens:**
Chart data fetching looks simple — it is just OHLCV bars. Developers reach for `yfinance.download()` directly rather than routing through the abstraction layer, especially because the chart endpoint is a new React frontend concern and the developer does not connect it to the existing backend data layer.

**How to avoid:**
- The chart OHLCV endpoint must call the same vendor abstraction used by the analysis agents: route through `interface.py`'s `VENDOR_METHODS` routing pattern
- Add a `get_historical_ohlcv(ticker, period, interval)` method to the vendor interface and implement it for all current vendors (yfinance, Tradier)
- The chart endpoint in FastAPI should call this interface method, not yfinance directly
- Write a test that confirms chart data and analysis data for the same ticker/date return the same closing price

**Warning signs:**
- `import yfinance as yf` appears in the chart router file without going through `interface.py`
- Chart shows a different closing price for a past date than what is stored in the analysis log for the same ticker/date
- Vendor switch test (changing `DATA_VENDOR` env var) does not affect the chart data source

**Phase to address:** TradingView charts integration phase, backend chart data endpoint design.

---

## Minor Pitfalls

---

### Pitfall 13: React Chart Component Causing Performance Degradation on Tab Switch

**What goes wrong:**
The TradingView chart component is mounted once on the Analysis tab and kept alive in the DOM as the user switches between tabs. The chart component holds a live `ResizeObserver` and redraws on every parent container resize event. In a tabbed layout where tabs are hidden via CSS (`display: none`), the chart may still receive resize events and attempt to redraw, consuming CPU in the background.

**How to avoid:**
- Unmount the chart component (not just hide it) when the user navigates away from the chart tab — use conditional rendering in React (`{activeTab === 'chart' && <ChartComponent />}`)
- The `useEffect` cleanup must call `chart.remove()` on unmount — this releases the canvas and unregisters the `ResizeObserver`
- Use `React.memo` or `useMemo` to avoid re-rendering the chart on unrelated state changes in parent components

**Phase to address:** TradingView charts integration phase, React component architecture.

---

### Pitfall 14: Alpaca Paper Trading Account Needing Manual Setup Steps Not in Code

**What goes wrong:**
Alpaca paper trading accounts require manual activation via the dashboard before API access works. Options trading (even in paper mode) requires enabling "options trading" in the account settings separately from paper access. A developer who generates API keys but skips account configuration will receive cryptic `403` errors with messages like "account does not have the required feature enabled."

**How to avoid:**
- Document the one-time manual setup steps in the developer setup guide: (1) create paper account, (2) enable options trading in account settings, (3) generate paper API keys from the paper section of the dashboard
- Add a startup health check endpoint that calls `GET /v2/account` and verifies `options_trading_level >= 1` before the paper trading feature is enabled
- Surface clear error messages: if the health check fails, the paper trading UI section should show "Alpaca account configuration required — see setup guide" rather than a generic error

**Phase to address:** Alpaca paper trading integration phase, developer setup.

---

### Pitfall 15: Track Record Dashboard Mixing Options and Equity Recommendation Quality

**What goes wrong:**
The track record dashboard aggregates all AI recommendations into a single win rate and expectancy score. Options recommendations (complex multi-leg strategies with defined max profit/loss) and equity directional calls (open-ended P&L) have fundamentally different return distributions. Mixing them into one aggregate score produces a metric that accurately describes neither category.

**How to avoid:**
- Separate track record views for equity directional calls and options strategy recommendations
- Each view uses metrics appropriate to the asset class: for equities, directional accuracy and P&L; for options, whether the trade expired in profit relative to max risk (risk-adjusted return)
- The dashboard header must clearly label which category is displayed

**Phase to address:** Track record dashboard phase, UI design.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Polling order status instead of Alpaca WebSocket for fill confirmation | Simpler to implement, no persistent connection | Extra latency on fill detection; O(N) requests for N open orders | Acceptable for v1.2 (low order volume), revisit if orders per session exceed 10 |
| Fetching chart data directly from yfinance in chart endpoint | Fast to build | Diverges from vendor abstraction; breaks on vendor swap | Never — route through interface.py always |
| Using win rate as primary headline metric | Easy to calculate and explain | Misleads users; mathematically incomplete | Never as a standalone headline metric |
| Storing paper trade outcomes in the same JSON file as analysis decisions | Single file to manage | Schema versioning complexity; concurrent write risk | Only if atomic write locking is implemented |
| Hardcoding assumed position size ($1,000 per trade) | Removes a config surface | Wrong for users with different capital | Acceptable for v1.2 MVP if clearly labeled in UI |
| alpaca-trade-api (old SDK) instead of alpaca-py | Existing tutorials and examples | Deprecated, no new features, community support declining | Never — migrate to alpaca-py |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Alpaca paper trading | Using live-environment base URL with paper keys | Initialize `TradingClient(paper=True)` explicitly; assert base URL at startup |
| Alpaca paper trading | Calling sync `client.submit_order()` inside `async def` FastAPI route | Wrap with `asyncio.to_thread()` or run in a `ThreadPoolExecutor` |
| Alpaca options | Submitting multi-leg bracket orders for options | Alpaca does not support bracket orders for options; submit legs individually or scope to equities only |
| lightweight-charts v5 | Using v4 series creation API (`addLineSeries()`) | Use `chart.addSeries(CandlestickSeries, options)` — import series type from library |
| lightweight-charts + React | Creating chart outside `useEffect` or missing cleanup | Always initialize in `useEffect`, always return `chart.remove()` as cleanup function |
| lightweight-charts + React StrictMode | Double-mount creating two chart instances | Ensure `chart.remove()` cleanup runs before re-mount; check for duplicate canvas elements |
| JSON trade log | Appending to log without file locking from multiple concurrent analysis runs | Use atomic write (write to temp file, rename) or a write-queue per ticker |
| Track record scoring | Scoring recommendations on the day they are made | Scoring requires deferred evaluation after N trading days; store as `pending_outcome` until then |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| lightweight-charts re-rendering on every parent state change | Chart flickers or redraws constantly; high CPU usage when filtering/searching | Wrap chart component in `React.memo`; separate chart state from analysis state | On any parent component state change if not memoized |
| Fetching full OHLCV history for chart on every tab switch | Noticeable delay re-entering chart tab; repeated yfinance calls in network log | Cache chart data in component state or frontend store for the session; only re-fetch if ticker changes | After 2-3 tab switches with slow network |
| Polling Alpaca for all open order statuses on every dashboard load | Track record dashboard slow to load; many Alpaca API requests per page view | Poll only `pending` orders; mark terminal-state orders (`filled`, `canceled`) as final in local store | When more than 5-10 open orders exist simultaneously |
| Fetching price history for scoring all recommendations on dashboard load | Track record dashboard times out for users with many recommendations | Paginate recommendations; fetch outcome prices lazily on scroll or on-demand | After ~50+ recommendations in the log |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Alpaca live API keys stored in the same `.env` as paper keys | Accidental live order submission during development | Separate `.env.paper` and `.env.live`; default environment is always paper; live keys require explicit `ENV=live` override |
| Alpaca API keys committed to version control | Unauthorized trading or account access | `.env` and all `*.env.*` variants in `.gitignore`; pre-commit hook to block credential patterns |
| Chart endpoint exposing raw ticker price history without auth | Leaks portfolio positions if ticker is inferred from position logs | Chart endpoint should require the same session auth as the analysis endpoint; no unauthenticated price history |
| Paper trading order history accessible to other users | Leaks trading strategy | If multi-user support is ever added, scope all Alpaca and log queries by user ID from the start |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Win rate as headline stat on track record | User misreads a 40% win rate system as losing when it may be profitable | Primary headline: Expectancy ($ per recommendation). Win rate shown as context only. |
| Paper trading results labeled as "performance" without simulation disclaimer | User overestimates AI edge; disappointment when going live | Persistent banner: "Simulated performance — no slippage or execution delays." |
| Chart without analysis decision annotation | User cannot connect AI recommendation to price action | Vertical marker on chart at analysis date; tooltip with decision, confidence, and target |
| Track record showing recommendations with no defined outcome window | "Is this a 1-day call or a 3-month call?" — scoring becomes ambiguous | Every recommendation must show the evaluation horizon (e.g., "5-day outlook") set at analysis time |
| Orders submitted to Alpaca with no visible confirmation or failure feedback | User doesn't know if paper trade was placed | Order status indicator in UI: Submitted → Accepted → Filled / Rejected with timestamp |

---

## "Looks Done But Isn't" Checklist

- [ ] **TradingView chart:** Appears to render — verify `chart.remove()` cleanup runs on unmount and no duplicate canvas elements exist in StrictMode
- [ ] **TradingView chart:** Data displays — verify chart timestamp aligns with analysis decision timestamp and uses the same data vendor as the analysis pipeline
- [ ] **Alpaca paper trading:** Order submits without error — verify the order reaches `filled` status (not just `new`) before marking it as executed
- [ ] **Alpaca paper trading:** Environment appears correct — verify `TradingClient` is initialized with `paper=True` and the base URL is `paper-api.alpaca.markets`
- [ ] **Recommendation scoring:** Metrics are calculated — verify scores are NOT generated for recommendations made today (outcome is unknowable until after evaluation window)
- [ ] **Recommendation scoring:** Schema looks correct — verify historical pre-v1.2 logs are excluded from scoring metrics, not just showing as zero-score entries
- [ ] **Track record dashboard:** P&L is displayed — verify position size assumption is explicitly labeled in the UI and adjustable
- [ ] **Track record dashboard:** Options and equity recommendations appear together — verify they are separated into distinct views with appropriate metrics per asset class
- [ ] **Paper trading + SSE:** Order submission works locally — verify under concurrent SSE streams that Alpaca calls do not block SSE event delivery (test with two browser tabs)

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| lightweight-charts v4 API used throughout (wrong version) | MEDIUM | Migrate `addLineSeries` → `addSeries(LineSeries, opts)` per component; test each chart type |
| Alpaca live keys accidentally used in development | HIGH | Immediately rotate both paper and live keys; audit order history for unintended submissions; add env guards |
| Trade log schema missing fields needed for scoring | MEDIUM | Add `schema_version` field; new logs use v1.2 schema; run a one-time backfill script that adds `price_at_decision` from historical yfinance data with explicit "retroactively filled" flag; track record starts from v1.2 date |
| Win rate used as primary metric already in production | LOW-MEDIUM | Add expectancy calculation without removing win rate; reorder display to make expectancy primary; add inline explanation of the difference |
| Alpaca sync calls blocking event loop | MEDIUM | Wrap all `client.*` calls with `asyncio.to_thread()`; search codebase for `client.submit_order` without `await` |
| Chart data vendor divergence from analysis vendor | LOW | Route chart endpoint through `interface.py`; add price consistency test |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| lightweight-charts v5 API incompatibility (P1) | Charts integration — chart component setup | Render a candle chart with v5 API in Vite + React StrictMode, confirm no duplicate canvas, confirm cleanup |
| Chart-vendor divergence from analysis (P12) | Charts integration — backend chart data endpoint | Test: same ticker/date returns same closing price from chart endpoint and analysis log |
| React StrictMode double-mount memory leak (P1) | Charts integration — component lifecycle | Open DevTools heap snapshot before and after mounting/unmounting chart 10 times; confirm no growth |
| Alpaca key/URL environment mismatch (P2) | Alpaca integration — environment setup | Startup assertion test: wrong key type triggers config error, not silent 401 |
| Alpaca options multi-leg limitation (P3) | Alpaca integration — requirements scope | Document equity-only scope in requirements before writing any order submission code |
| FastAPI event loop blocking (P4) | Alpaca integration — API client design | Load test: concurrent SSE stream + order submission; confirm SSE delivery does not stall |
| Order status not tracked to final state (P9) | Alpaca integration — order lifecycle | Test: submitted paper order reaches `filled` status in tracking log within 60 seconds |
| Trade log schema insufficient (P7) | Scoring — schema design | Schema review: confirm v1.2 log includes `price_at_decision`, `target_horizon_days`, `schema_version` |
| Win rate as sole primary metric (P5) | Scoring — metrics definition | Dashboard spec review: expectancy must be the primary headline stat |
| Confidence score as proxy for accuracy (P11) | Scoring — metrics definition | Scoring calculation is based on outcome price comparison, not on `confidence_score` field |
| Paper fills overstating real performance (P6) | Track record — display design | Dashboard has slippage disclaimer and shows "simulated" label before any P&L number |
| Missing position size in P&L (P10) | Track record — display design | Every P&L figure in the dashboard has an associated position size assumption visible in the UI |
| Equity and options metrics mixed (P15) | Track record — UI design | Separate dashboard views confirmed in component design before implementation |

---

## Confidence Assessment

| Area | Confidence | Source Basis |
|------|------------|--------------|
| lightweight-charts v5 breaking changes | HIGH | Official migration guide, GitHub issue #1791, confirmed v5 release notes |
| Alpaca paper vs live environment separation | HIGH | Official Alpaca docs, community forum error reports |
| Alpaca options multi-leg paper trading gap | HIGH | Official Alpaca support page, community forum issue #14241 |
| FastAPI async event loop blocking | HIGH | Official FastAPI async documentation, multiple developer post-mortems |
| Win rate as misleading metric | HIGH | Multiple quantitative trading sources (Edge Wonk, TradesViz, TradeZella) confirm unanimously |
| Paper trading slippage overstatement | HIGH | Alpaca official post on paper vs live differences, Alpaca forum slippage thread |
| LangGraph side effect pattern for execution | MEDIUM | General LangGraph state docs; no specific paper trading integration guidance found |
| Deferred scoring evaluation architecture | MEDIUM | Derived from scoring methodology best practices; no direct source for this exact architecture |

---

## Sources

- [Upgrading to lightweight-charts v5 — GitHub Issue #1791](https://github.com/tradingview/lightweight-charts/issues/1791)
- [lightweight-charts v5 Migration Guide — Official Docs](https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5)
- [Primitives not syncing in React — GitHub Issue #1920](https://github.com/tradingview/lightweight-charts/issues/1920)
- [Advanced React Example — lightweight-charts Official Docs](https://tradingview.github.io/lightweight-charts/tutorials/react/advanced)
- [Alpaca Paper Trading — Official Docs](https://docs.alpaca.markets/docs/paper-trading)
- [Alpaca Common API Errors — Official Guide](https://alpaca.markets/learn/how-to-fix-common-trading-api-errors-at-alpaca)
- [Bracket Order for Options Error — Alpaca Forum #14241](https://forum.alpaca.markets/t/bracket-order-for-option-error-complex-orders-not-supported-for-options-trading/14241)
- [alpaca-py Getting Started — Official Docs](https://alpaca.markets/sdks/python/getting_started.html)
- [Paper Trading vs Live Trading — Alpaca Official](https://alpaca.markets/learn/paper-trading-vs-live-trading-a-data-backed-guide-on-when-to-start-trading-real-money)
- [Slippage: Paper vs Real Trading — Alpaca Forum](https://forum.alpaca.markets/t/slippage-paper-trading-vs-real-trading/2801)
- [10 Async Pitfalls in FastAPI — Medium](https://medium.com/@bhagyarana80/10-async-pitfalls-in-fastapi-and-how-to-avoid-them-60d6c67ea48f)
- [Top 7 FastAPI asyncio Best Practices — TechBuddies](https://www.techbuddies.io/2026/01/05/top-7-fastapi-asyncio-best-practices-for-non-blocking-web-apis/)
- [Win Rate as a Vanity Metric — TradeZella](https://www.tradezella.com/blog/win-rate)
- [Win Rate vs. Expectancy — UltraTrader](https://blog.ultratrader.app/the-1000000-mistake-why-your-win-rate-doesnt-matter-and-expectency-does/)
- [Beyond Win Rate: R-Value and Profit Factor — TradesViz](https://www.tradesviz.com/blog/what-is-r-value-profit-factor/)
- [Why Most Backtests Fail — Frontier Ledger](https://frontierledger.ai/foundations-core-concepts/why-most-backtests-fail-overfitting-look-ahead-bias-and-data-snooping)
- [Look-Ahead Bias in AI Trading Signals — arxiv 2601.13770](https://arxiv.org/pdf/2601.13770)

---
*Pitfalls research for: TradingView charts, Alpaca paper trading, recommendation scoring, track record dashboard — added to existing LangGraph + FastAPI + React trading analysis system*
*Researched: 2026-04-03*
