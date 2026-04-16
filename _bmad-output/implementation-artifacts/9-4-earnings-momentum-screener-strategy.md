# Story 9.4: Earnings Momentum Screener Strategy

Status: review

## Story

As a user,
I want an earnings momentum screener that detects post-earnings gap-ups with strong follow-through,
so that I can find stocks with institutional-quality earnings reactions worth trading.

## Tasks / Subtasks

- [x] Task 1: Post-earnings gap detection
  - [x] Identify earnings dates from yfinance calendar/earnings_dates
  - [x] Detect gap-up/gap-down on earnings day (open vs prior close)
  - [x] Filter for minimum gap threshold (configurable, default 3%)
  - [x] Track gap fill behavior in subsequent sessions
- [x] Task 2: 5-factor scoring system
  - [x] Gap size score (25% weight) — larger gaps score higher, capped at 15%
  - [x] Pre-earnings trend score (30% weight) — uptrend into earnings is bullish
  - [x] Volume score (20% weight) — earnings day volume vs 50-day average
  - [x] MA200 score (15% weight) — price above rising 200-day MA
  - [x] MA50 score (10% weight) — price above rising 50-day MA
- [x] Task 3: Grading and ranking
  - [x] Composite 0-100 from weighted factors
  - [x] Map to letter grade: A (80-100), B (60-79), C (40-59), D (0-39)
  - [x] Rank by composite score, return top N as TopPick entries
  - [x] Include gap percentage and grade in TopPick reasoning
- [x] Task 4: Assemble EarningsMomentumStrategy class
  - [x] Implement `ScreenerStrategy` protocol: `screen(config, llm) -> ScreenerResult`
  - [x] Register as "earnings" with display_name="Earnings Momentum", description="Post-earnings gap detection with 5-factor scoring — gap size, trend, volume, MA200, MA50"
  - [x] No LLM usage — quantitative factor scoring only
- [x] Task 5: Write tests
  - [x] Test: Gap detection correctly identifies >3% earnings gaps
  - [x] Test: Each factor scorer returns 0-100 range
  - [x] Test: Composite weights sum to 100% and produce correct grades
  - [x] Test: Full screen returns valid ScreenerResult sorted by score

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Detects post-earnings gaps using yfinance earnings_dates + price history
- 5-factor model: gap size 25%, pre-earnings trend 30%, volume 20%, MA200 15%, MA50 10%
- A/B/C/D grading with composite score in TopPick reasoning
- Handles edge cases: no recent earnings, insufficient history, weekend earnings dates

### File List
- `tradingagents/agents/screener/strategies/earnings.py` — NEW: Earnings momentum strategy implementation
