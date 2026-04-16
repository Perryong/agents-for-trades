# Story 11.2: Market Top Detector

Status: review

## Story

As a trader,
I want an automated market top detection system using O'Neil-style distribution day counting and sector rotation analysis,
so that I receive early warning when the market is forming a top and can reduce exposure before a correction.

## Acceptance Criteria

1. Distribution day counting follows O'Neil methodology: index down >0.2% on higher volume than previous session, within a rolling 25-session window
2. Leading stock deterioration is tracked (percentage of leaders breaking below key moving averages)
3. Defensive rotation signal compares XLU+XLP relative strength vs XLK+XLY
4. Output is a top probability score 0-100
5. 4+ distribution days within 25 sessions triggers elevated risk (probability >= 60)
6. Function is callable independently and returns structured output

## Tasks / Subtasks

- [x] Task 1: Create `detect_market_top()` in `tradingagents/services/market_signals.py` (AC: #1, #4, #5)
  - [x] Define `MarketTopSignal` Pydantic model with `top_probability` (0-100), `distribution_day_count`, `window_sessions` (25), `details`, `timestamp`
  - [x] Implement distribution day counter: close down >0.2% AND volume > previous session volume, rolling 25-session window
  - [x] Score mapping: 0-1 days = low (0-20), 2-3 = moderate (20-50), 4-5 = elevated (60-75), 6+ = high (80-100)

- [x] Task 2: Add leading stock deterioration signal (AC: #2)
  - [x] Track percentage of top 20 market-cap leaders below their 50-day moving average
  - [x] >50% leaders deteriorating adds +15 to top probability
  - [x] >75% leaders deteriorating adds +25 to top probability

- [x] Task 3: Add defensive rotation signal (AC: #3)
  - [x] Compare 20-day relative strength of (XLU + XLP) vs (XLK + XLY)
  - [x] Defensive outperformance (ratio > 1.05) adds +10 to top probability
  - [x] Strong defensive outperformance (ratio > 1.15) adds +20 to top probability

- [x] Task 4: Write unit tests
  - [x] Test distribution day counting with known price/volume data
  - [x] Test 4+ distribution days returns probability >= 60
  - [x] Test leading stock deterioration contribution
  - [x] Test defensive rotation signal contribution
  - [x] Test probability clamped to 0-100 range
  - [x] Test with empty/insufficient data returns low probability

## Dev Notes

### Architecture Compliance

- **New file:** `tradingagents/services/market_signals.py` — shared by both 11.2 and 11.3 (FTD detector)
- **O'Neil methodology:** "How to Make Money in Stocks" — distribution day = index closes down >0.2% on volume higher than previous day, counted over rolling 25 trading sessions
- **No external API calls in the function itself** — accepts pre-fetched price/volume data as input parameters

### Key Design Decisions

- Top probability is composite: base score from distribution days + additive modifiers from leaders and rotation
- Final probability clamped to [0, 100]
- Function is stateless — caller provides the data, function returns the signal

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Completion Notes List

- Created `detect_market_top()` in `tradingagents/services/market_signals.py` with O'Neil distribution day counting.
- Distribution days: down >0.2% on higher volume in 25-session rolling window.
- Leading stock deterioration and defensive sector rotation (XLU+XLP vs XLK+XLY) as additive modifiers.
- 4+ distribution days triggers elevated risk (probability >= 60).
- Output clamped to 0-100 range.

### File List

- `tradingagents/services/market_signals.py` (NEW: detect_market_top function)
