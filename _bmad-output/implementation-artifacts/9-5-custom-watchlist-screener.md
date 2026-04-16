# Story 9.5: Custom Watchlist Screener

Status: review

## Story

As a user,
I want a screener that analyzes only the tickers in my personal watchlist using momentum and volume signals plus LLM ranking,
so that I can get AI-powered insights on stocks I am already tracking.

## Tasks / Subtasks

- [x] Task 1: Watchlist input handling
  - [x] Accept watchlist tickers from config (passed via ScreenRequest)
  - [x] Validate tickers exist in yfinance — skip invalid with warning
  - [x] Return descriptive error message if watchlist is empty
- [x] Task 2: Signal computation on watchlist tickers
  - [x] Compute momentum signals (RSI, rate of change, MA crossovers) for each ticker
  - [x] Compute volume signals (volume vs 50-day average, unusual activity)
  - [x] Aggregate into per-ticker signal summary
- [x] Task 3: LLM ranking of watchlist candidates
  - [x] Pass signal summaries to LLM for qualitative ranking
  - [x] LLM produces ordered list with reasoning per ticker
  - [x] Parse LLM output into TopPick entries
- [x] Task 4: Assemble WatchlistStrategy class
  - [x] Implement `ScreenerStrategy` protocol: `screen(config, llm) -> ScreenerResult`
  - [x] Register as "watchlist" with display_name="My Watchlist", description="Screen your personal watchlist with momentum + volume signals and LLM ranking"
  - [x] If config has no watchlist or empty list, return ScreenerResult with error message and no picks
- [x] Task 5: Write tests
  - [x] Test: Empty watchlist returns error message in result
  - [x] Test: Invalid tickers are skipped gracefully
  - [x] Test: Signal computation produces expected fields for valid tickers
  - [x] Test: Full screen with mock LLM produces valid ScreenerResult

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Only strategy that uses LLM — momentum/volume signals fed to LLM for qualitative ranking
- Empty watchlist returns ScreenerResult with market_overview containing error, empty picks list
- Invalid tickers logged as warnings and skipped, not fatal
- Reuses signal computation patterns from momentum strategy for consistency

### File List
- `tradingagents/agents/screener/strategies/watchlist.py` — NEW: Watchlist screener strategy implementation
