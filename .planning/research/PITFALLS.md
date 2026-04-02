# Domain Pitfalls — Stock Recommendation / Screening System

**Domain:** AI-driven stock screening added to existing LLM-based trading framework
**Researched:** 2026-04-02
**Context:** Adding v1.1 screener to TradingAgents (LangGraph + FastAPI + React). Existing full
analysis pipeline is compute-heavy and LLM-expensive. Pre-filter must gate LLM access.

---

## Critical Pitfalls

Mistakes that cause rewrites, runaway LLM bills, or downstream corrupted analysis.

---

### Pitfall 1: Screener Directly Triggering the Full Analysis Pipeline

**What goes wrong:** The screener result surface (frontend tab, CLI output) includes a
"Run Analysis" button that fires the full LangGraph pipeline for ALL screened picks
automatically — or the screener agent is wired as a graph node that conditionally kicks off
analysis without explicit user confirmation.

**Why it happens:** It feels natural to wire screener output directly into analysis input.
LangGraph's graph structure makes it easy to add an edge from the screener node to the
`market_analyst` node, and developers do it "just to test" and forget to remove it.

**Consequences:**
- 20-50 screened candidates × full pipeline = 20-50 LLM call chains per screener run
- At ~30 LLM calls per analysis, that is 600-1500 API calls from one screener invocation
- Cost spike can exceed daily OpenAI spend budgets in a single run
- Pipeline was explicitly declared Out of Scope for auto-triggering in PROJECT.md

**Prevention:**
- The screener subgraph must have no outgoing edges to analysis nodes in StateGraph
- The screener result must land in a separate `ScreenerState` or dedicated state field,
  not in `AgentState` (which signals the analysis pipeline)
- Frontend "Analyze" action requires an explicit per-ticker user click — no bulk action
- Add a runtime guard in the API handler: if `screener_mode` and `tickers > 1`, reject
  auto-analysis requests with HTTP 422

**Detection:** If a screener run takes more than 60 seconds, something is invoking the
analysis pipeline. Normal screener pass should complete in 5-15 seconds.

**Phase:** Pre-filter data layer + LLM screener agent wiring phases must enforce this boundary.

---

### Pitfall 2: yfinance 429 Errors Silently Corrupting Screener Output

**What goes wrong:** When scanning 500-5000 tickers for pre-filter criteria (volume movers,
unusual activity), yfinance returns HTTP 429 Too Many Requests. If the error is swallowed
or the ticker is simply dropped from results, the screener silently produces an incomplete
candidate list — tickers that would have passed the filter are missed, and the user has no
indication the scan was partial.

**Why it happens:** yfinance is an unofficial scraper of Yahoo Finance endpoints. As of late
2024, Yahoo tightened limits — users report hitting blocks after ~950 tickers in a single
session. Bulk loops that were working in 2023 break in 2025. Common error handling patterns
use `try/except` and `continue`, which drops the ticker without surfacing the failure.

**Consequences:**
- Screener appears to work but misses entire sectors or index constituents that were rate-
  limited during the scan window
- LLM screener agent ranks a biased subset, producing structurally misleading picks
- Hardest class of bug to diagnose because output looks valid

**Prevention:**
- Never iterate individual tickers in a loop. Use `yf.download(tickers_list, ...)` in
  chunks of 80-100 tickers maximum with `threads=True` and `group_by='ticker'`
- Add exponential backoff with jitter: initial 2s, max 60s, 3 retries per chunk
- Track `fetch_attempted` vs `fetch_succeeded` per run; surface coverage percentage in
  screener output metadata (`"coverage": "4731/5000 (94.6%)"`)
- If coverage drops below a configurable threshold (default 80%), abort the run and
  surface a warning rather than returning a partial result silently
- Cache successful ticker data for the session window (not across market sessions)

**Detection:** Add a `screener_coverage` metric to the API response. Alert if `< 90%`.

**Phase:** Pre-filter data layer phase must implement chunk-based fetching and coverage
tracking before any LLM screener agent is built on top of it.

---

### Pitfall 3: Stale Pre-Filter Data Feeding the LLM Screener

**What goes wrong:** Screener pre-filter results are cached aggressively (or at all across
market sessions). The LLM screener agent receives a candidate list that reflects
yesterday's volume movers or last week's sector momentum. It produces confident-sounding
rationale for picks that have already moved, reversed, or been halted.

**Why it happens:** Caching is added as a performance optimization after rate limit problems
(see Pitfall 2). Developer sets a long TTL (hours or days) to reduce yfinance calls. The
data feels "good enough" because tickers don't change — but prices and volume do.

**Consequences:**
- LLM narrative describes a momentum move that ended 18 hours ago as "current"
- User acts on a pick that has already gapped up 8% and reversed
- Hard to detect because picks often look plausible — names are real, narrative is coherent

**Prevention:**
- Pre-filter cache TTL must be tied to market session boundaries, not wall-clock time:
  - During market hours (9:30 AM - 4:00 PM ET): TTL = 15 minutes maximum
  - After hours / pre-market: TTL = until next market open (data is exploratory only)
  - Weekend: Surface explicit "markets closed" label in screener UI
- Cache key must include the market session date, not just the date string
- LLM screener prompt must include a `data_as_of` timestamp in the context block so
  the model cannot confuse the data age
- Screener results in frontend must display "Data as of: [timestamp]" prominently — not
  buried in a tooltip

**Detection:** If screener results never change between two runs made 4+ hours apart during
market hours, the cache is almost certainly misconfigured.

**Phase:** Pre-filter data layer phase. TTL logic must be implemented before the LLM agent
is written — the agent inherits whatever freshness the data layer provides.

---

### Pitfall 4: LLM Screener Running on Too Many Candidates

**What goes wrong:** The programmatic pre-filter passes 200-500 "candidates" to the LLM
screener agent. The agent receives a large context window containing data for all candidates
and is asked to rank them. This produces several failure modes simultaneously.

**Why it happens:** Developers set the pre-filter threshold too generously ("let the LLM
decide") or fail to tune the filter criteria tightly enough. Volume filter set at 100K ADV
instead of 500K passes too many mid-cap names. No hard cap on candidates entering the LLM
step.

**Consequences:**
- Input tokens balloon: 200 candidates × ~150 tokens each = 30,000 input tokens per call
  at GPT-4o pricing (~$0.15 per run × daily use = $54/month just for screener)
- LLM reasoning degrades with very large candidate lists — attention diffusion causes
  arbitrary ranking artifacts, not genuine analysis
- Latency becomes unacceptable (30+ second screener calls undermine the UX)
- Response may be truncated by context window limits, silently dropping candidates

**Prevention:**
- Hard cap: Pre-filter MUST pass a maximum of 50 candidates to the LLM step. This is
  a configuration constant, not a soft guideline
- Pre-filter criteria must be tuned to produce 20-50 results from a 5000-ticker universe:
  - Relative volume >= 2.0x 30-day average AND
  - Price >= $5 (eliminates penny stocks) AND
  - Market cap >= $500M (eliminates illiquid micro-caps) AND
  - At least one of: unusual options activity, gap >= 2%, sector in top-3 momentum
- If pre-filter produces > 50 results, apply secondary sort (by relative volume desc)
  and truncate — do not pass all results to LLM
- Token budget the screener prompt explicitly: measure output at design time, not runtime

**Detection:** Log `input_token_count` for every screener LLM call. Alert if > 15,000
tokens. Monitor LLM cost per screener run in observability layer.

**Phase:** LLM screener agent phase. The 50-candidate cap must be enforced in the pre-
filter output contract, documented in the interface before the LLM agent is written.

---

### Pitfall 5: Screener AgentState Pollution Corrupting Analysis Runs

**What goes wrong:** The screener writes its candidate list and ranking rationale into the
main `AgentState` dict. A subsequent analysis run for a different ticker reads stale
screener fields from state and the LLM receives context contaminated with screener output
about different tickers.

**Why it happens:** `AgentState` is a shared dict in the existing system. It is tempting to
add `screener_candidates`, `screener_ranking`, and `screener_rationale` fields directly to
it because all other agent outputs live there. But the screener operates across many tickers
simultaneously while analysis operates on one ticker at a time — they have different
cardinality.

**Consequences:**
- Fundamentals analyst receives context that includes screener rationale for NVDA while
  analyzing AAPL
- Risk manager sees "screener flag: unusual options activity" that belongs to a different
  pick and inflates its risk score
- These contamination bugs are intermittent and timing-dependent, making them very hard
  to reproduce

**Prevention:**
- Screener must use a separate `ScreenerState` TypedDict, not `AgentState`
- Screener results are stored as a separate endpoint response or dedicated Redux/Zustand
  slice in frontend — they do not flow into the analysis pipeline state
- Analysis pipeline state must be initialized fresh per ticker/run — never reused across
  separate analysis invocations
- Add an explicit field exclusion check: if `screener_*` keys appear in `AgentState` at
  pipeline entry, raise a validation error

**Detection:** If analysis outputs mention tickers not in the current run's input, state
contamination has occurred.

**Phase:** Screener integration phase must define `ScreenerState` as a separate type
before wiring any nodes.

---

## Moderate Pitfalls

---

### Pitfall 6: Momentum vs. Mean-Reversion Signal Confusion

**What goes wrong:** The pre-filter uses volume spike + price gap as the primary signal,
which identifies short-term momentum candidates. The LLM screener is then prompted with
generic language like "best stocks to analyze today" without specifying the regime. The
LLM mixes momentum reasoning with mean-reversion reasoning in its rationale, producing
inconsistent rankings.

**Why it happens:** The signal type (momentum) is implicit in the filter criteria but never
explicitly passed to the LLM. The LLM applies its training priors, which include both
momentum and mean-reversion frameworks, and blends them arbitrarily.

**Consequences:**
- LLM recommends a stock that has already moved 15% as a "breakout play" (momentum framing)
  alongside a stock that dropped 20% as a "value opportunity" (mean-reversion framing)
  in the same ranked list, with no distinction made
- User cannot assess which recommendation style to apply when running full analysis

**Prevention:**
- Screener prompt must explicitly declare the signal regime: "The following candidates were
  selected because they show unusual volume and price momentum. Rank them by momentum
  continuation probability, not value or mean-reversion potential."
- If the system later supports mean-reversion screening (e.g., oversold scanners), use
  separate prompt templates per screener mode — never blend regimes in one prompt
- The frontend "Screener Type" selector (momentum / unusual activity / fundamental) must
  pass the selected mode into the LLM system prompt

**Phase:** LLM screener agent phase — prompt engineering.

---

### Pitfall 7: Survivorship Bias in Screener Universe

**What goes wrong:** The ticker universe used for pre-filtering contains only currently
active, listed stocks. Delisted, halted, or recently acquired tickers are absent. This
does not corrupt today's picks but does corrupt any historical comparison the LLM makes
("this pattern worked before") and causes subtle sector weighting errors.

**Why it happens:** yfinance and most free data sources return only active tickers. There
is no standard delisted-securities endpoint in yfinance. Developers use S&P 500, NASDAQ
100, or Russell 2000 constituent lists without noting that these lists reflect current
membership, not historical membership.

**Consequences:**
- LLM narrative cites sector patterns that only appear valid because failures have been
  removed from the reference universe
- Sector momentum scores overstate the success rate of previous similar setups
- Moderate in v1.1 because backtesting is Out of Scope — but will become critical in v1.2
  when backtesting is added

**Prevention:**
- For v1.1: Add a disclaimer in the screener prompt and UI: "Universe: current active
  listings only. Historical sector comparisons may reflect survivorship bias."
- Document this explicitly as a v1.2 concern in phase retrospective
- Do not let the LLM screener agent make historical pattern claims ("stocks like this
  historically perform well") — restrict prompt to current-signal ranking only

**Phase:** LLM screener agent prompt design. Flag for v1.2 backtesting phase.

---

### Pitfall 8: Tradier Rate Limits During Multi-Ticker Options Activity Scan

**What goes wrong:** The pre-filter includes unusual options activity as one of its signals.
For 50-200 candidate tickers, this requires individual Tradier API calls to check options
volume. Tradier's production rate limit is 120 requests/minute. A naive sequential scan of
200 tickers for options activity exhausts this limit in under 2 minutes, triggering 429
errors on the options data portion of the scan.

**Why it happens:** The existing system makes one Tradier call per analysis run (one ticker),
so the rate limit was never a concern. The screener fundamentally changes the access pattern
from single-ticker to multi-ticker.

**Consequences:**
- Options activity signal is missing for ~40% of candidates (those past the rate limit)
- Pre-filter silently degrades: some tickers pass without options check, others fail
- The existing Tradier abstraction layer has no rate-limit-aware pooling built in

**Prevention:**
- Options activity check in pre-filter should run AFTER basic volume/price/market-cap
  filters have already reduced the universe to <= 50 candidates — never on the full 5000
- Implement a request pool with a 120 req/min token bucket for Tradier calls in the
  screener context (the existing single-ticker path does not need this)
- If a Tradier options check fails with 429, fall back to yfinance options volume estimate
  for that ticker rather than dropping it from candidates
- Log Tradier usage per screener run: `tradier_calls_made`, `tradier_calls_failed`

**Phase:** Pre-filter data layer phase, specifically when wiring the options activity signal.

---

### Pitfall 9: Screener Results Not Timestamped in Frontend

**What goes wrong:** The screener results tab in the frontend displays picks without a
visible "generated at" timestamp. The user runs the screener at 9:45 AM, leaves for a
meeting, returns at 2:30 PM, and acts on picks that are now 5 hours stale — with the market
having moved significantly in between.

**Why it happens:** Timestamps are treated as a "nice to have" UI detail and deferred.
The API response includes a timestamp field but the frontend component does not render it.

**Consequences:**
- User acts on stale screener output believing it to be current
- If picks have reversed, this creates a negative outcome directly attributable to the
  product, not to user judgment

**Prevention:**
- Screener results component must display timestamp prominently (not in a tooltip):
  "Screened at: 10:23 AM ET — refresh for current data"
- Add a "stale" visual indicator if results are older than the cache TTL (15 min during
  market hours)
- The API endpoint must always include `screened_at` (ISO 8601) and `market_session`
  ("open" / "pre-market" / "after-hours" / "closed") in the response envelope

**Phase:** Frontend screener UI phase.

---

### Pitfall 10: Overly Verbose LLM Screener Prompts

**What goes wrong:** The screener prompt includes the system context from the full analysis
pipeline (trading philosophy, risk parameters, options strategy context, debate rules) as
boilerplate preamble. This was copy-pasted from the existing agent prompt templates as a
starting point and never trimmed.

**Why it happens:** Existing agents use `quick_thinking_llm` / `deep_thinking_llm` with
shared prompt scaffolding. It is natural to start from a working template.

**Consequences:**
- Options strategy context is irrelevant at the screening stage; it adds ~500-800 tokens
  per call with zero ranking value
- The screener runs on every system startup for fresh data; verbose prompts at 3000+ tokens
  make this expensive at scale
- Model may attempt to apply options strategy logic to screening decisions, producing
  incoherent rationale

**Prevention:**
- The screener agent must have its own minimal prompt template — do not inherit from
  existing agent templates
- Screener system prompt should be <= 300 tokens: role (stock screener), signal type
  (momentum), output format (ranked list of max 5, with one-sentence rationale each)
- Measure token count at design time. If screener system prompt exceeds 300 tokens,
  treat that as a build failure

**Phase:** LLM screener agent phase — prompt design.

---

## Minor Pitfalls

---

### Pitfall 11: Screener Tab Visible During Active Analysis Run

**What goes wrong:** User runs full analysis for AAPL. While it is streaming, they switch
to the Screener tab and trigger a new screener run. The SSE stream for the analysis run
collides with the screener's API response in the frontend state, causing the progress
stepper to either stall or show screener metadata as analysis progress events.

**Prevention:**
- Screener API calls must use a separate endpoint (`/api/screener`) with its own
  response model — never share the SSE `/api/analyze` stream endpoint
- Frontend must disable the "Run Screener" button while an analysis SSE stream is active
- The two features must have completely isolated state slices in the frontend store

**Phase:** Frontend integration phase.

---

### Pitfall 12: User Overwhelm from Too Many Screener Picks

**What goes wrong:** The LLM screener returns 10-15 picks. The frontend displays all of
them in a list with full rationale for each. The user cannot determine which is the single
most actionable pick and feels pressure to analyze multiple tickers, defeating the purpose
of the screener.

**Prevention:**
- Hard cap screener output at 5 picks maximum (3 is better for most users)
- Display picks in a ranked card layout with a clear #1 / #2 / #3 ordering — not a flat
  list
- Show only the one-sentence rationale inline; full rationale is expandable on click
- The "Analyze" CTA on each pick card should be visually prominent on the #1 pick and
  subdued on lower-ranked picks to guide attention

**Phase:** Frontend screener UI phase.

---

### Pitfall 13: Screener Criteria Not Configurable by User

**What goes wrong:** Pre-filter thresholds (relative volume, minimum price, minimum market
cap) are hardcoded constants. User with a different trading style (e.g., small-cap focus
at $1-5 price range) cannot adapt the screener to their universe.

**Prevention:**
- Expose the 3-4 primary pre-filter thresholds as user-configurable parameters in the
  frontend config sidebar (matching the pattern of existing config fields)
- Provide sensible defaults (min price: $5, min market cap: $500M, min rel volume: 2.0x)
- Validate input ranges server-side to prevent pathological configurations (e.g., min
  price: $0 passing all 10,000 OTC tickers to the LLM)

**Phase:** Frontend screener UI phase, after core screener is functional.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Pre-filter data layer | yfinance 429 on bulk scan (Pitfall 2) | Chunk-based fetch (max 100 tickers/batch), exponential backoff, coverage tracking |
| Pre-filter data layer | Stale cache across market sessions (Pitfall 3) | Session-boundary TTL, `data_as_of` field in all responses |
| Pre-filter data layer | Tradier rate limit on options signal (Pitfall 8) | Apply options check only after volume/price filter; token bucket for Tradier |
| LLM screener agent wiring | Auto-triggering analysis pipeline (Pitfall 1) | `ScreenerState` separate from `AgentState`; no graph edges to analysis nodes |
| LLM screener agent wiring | State contamination (Pitfall 5) | Dedicated `ScreenerState` type; fresh `AgentState` init per analysis run |
| LLM screener agent wiring | Too many candidates into LLM (Pitfall 4) | Hard cap: 50 candidate max before LLM step; enforce in pre-filter output contract |
| LLM screener agent prompting | Verbose prompts (Pitfall 10) | Own minimal template; <= 300 token system prompt |
| LLM screener agent prompting | Regime confusion (Pitfall 6) | Explicit signal-type declaration in prompt; separate templates per screener mode |
| Frontend screener UI | No timestamp on results (Pitfall 9) | `screened_at` always in API envelope; stale indicator in UI |
| Frontend screener UI | Too many picks / flat ranking (Pitfall 12) | 5-pick hard cap; ranked card layout; subdued CTAs on lower picks |
| Frontend screener UI | SSE collision with analysis stream (Pitfall 11) | Separate endpoints; disable screener during active analysis |

---

## Confidence Assessment

| Pitfall Area | Confidence | Source Basis |
|--------------|------------|--------------|
| yfinance rate limiting behavior | HIGH | GitHub issues #2128, #2422, #2614 confirm 429 at ~950 tickers post late 2024 |
| Tradier rate limits (120 req/min) | HIGH | Official Tradier API documentation |
| LLM cost at scale (token math) | HIGH | Official pricing + documented token counts |
| Pipeline auto-trigger risk | HIGH | Inferred directly from PROJECT.md Out of Scope declaration |
| State contamination pattern | MEDIUM | LangGraph shared state architecture docs + general multi-agent patterns |
| Momentum/mean-reversion confusion | MEDIUM | Academic trading literature + general LLM prompt sensitivity findings |
| Survivorship bias | HIGH | Quantified in backtesting literature (CAGR drop from 46% to 16% in one study) |
| UX overload patterns | MEDIUM | Trading app UX research + general information overload literature |
| Data freshness / stale cache | HIGH | Multiple financial data observability sources confirm session-boundary TTL necessity |

---

## Sources

- [yfinance Rate Limiting Issue #2128](https://github.com/ranaroussi/yfinance/issues/2128)
- [yfinance YFRateLimitError Issue #2422](https://github.com/ranaroussi/yfinance/issues/2422)
- [yfinance Bulk Download Rate Limit Issue #2614](https://github.com/ranaroussi/yfinance/issues/2614)
- [Why yfinance Keeps Getting Blocked — Medium](https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01)
- [Rate Limiting and API Best Practices for yfinance — Sling Academy](https://www.slingacademy.com/article/rate-limiting-and-api-best-practices-for-yfinance/)
- [Tradier Rate Limiting — Official Docs](https://docs.tradier.com/docs/rate-limiting)
- [Survivorship Bias in Momentum Rotational Strategies — Price Action Lab](https://www.priceactionlab.com/Blog/2019/11/survivorship-bias-in-backtests-of-momentum-rotational-strategies/)
- [LLM Cost Optimization: Token Strategies 2025 — SparkCo](https://sparkco.ai/blog/optimize-llm-api-costs-token-strategies-for-2025)
- [Trading Platform UX Design No-Nos — DevExperts](https://devexperts.com/blog/trading-platform-ux-ui-design-no-nos/)
- [Data Freshness and Business Decision-Making — OWOX](https://www.owox.com/blog/articles/data-freshness-and-business-decision-making)
- [The Real Cost of Delayed Market Data — United Fintech](https://www.unitedfintech.com/blog/the-real-cost-of-delayed-market-data)
- [LangGraph Multi-Agent Architecture 2025 — Latenode](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)
