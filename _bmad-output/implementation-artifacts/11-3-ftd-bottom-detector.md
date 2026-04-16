# Story 11.3: Follow-Through Day (FTD) Bottom Detector

Status: review

## Story

As a trader,
I want automated Follow-Through Day detection tracking the correction-to-rally state machine,
so that I can identify confirmed market bottoms and increase exposure with confidence after corrections.

## Acceptance Criteria

1. State machine tracks four states: `no_correction` -> `correcting` -> `rally_attempt` -> `ftd_confirmed`
2. FTD definition: day 4+ of a rally attempt, index gains >1.5% on above-average volume
3. Quality score 0-100 reflects FTD strength (gain magnitude, volume ratio, breadth confirmation)
4. Dual tracking via SPY (primary) for broad market confirmation
5. Function returns current state, quality score, and transition history
6. State resets to `no_correction` after sustained uptrend or new correction

## Tasks / Subtasks

- [x] Task 1: Define FTD state machine in `tradingagents/services/market_signals.py` (AC: #1, #6)
  - [x] Define `FTDState` enum: `NO_CORRECTION`, `CORRECTING`, `RALLY_ATTEMPT`, `FTD_CONFIRMED`
  - [x] Define `FTDSignal` Pydantic model with `state`, `quality_score` (0-100), `rally_day_count`, `details`, `timestamp`
  - [x] Correction trigger: index drops >5% from recent high
  - [x] Rally attempt starts: first up day after correction low
  - [x] State reset: 10+ consecutive days above correction high returns to `NO_CORRECTION`

- [x] Task 2: Implement `detect_ftd()` function (AC: #2, #3, #4)
  - [x] Track rally day count from first up day after correction low
  - [x] FTD confirmed when: rally day >= 4, daily gain > 1.5%, volume > 50-day average volume
  - [x] Quality score formula: base 50 + (gain_pct - 1.5) * 10 + (volume_ratio - 1.0) * 15, clamped to [0, 100]
  - [x] Use SPY as primary tracking instrument

- [x] Task 3: Write unit tests
  - [x] Test state transitions: no_correction -> correcting on 5%+ drop
  - [x] Test rally_attempt starts on first up day after low
  - [x] Test FTD confirmed on day 4+ with >1.5% gain and above-average volume
  - [x] Test FTD NOT confirmed on day 3 (too early) even with big gain
  - [x] Test FTD NOT confirmed with below-average volume
  - [x] Test quality score increases with larger gains and higher volume
  - [x] Test state reset after sustained recovery

## Dev Notes

### Architecture Compliance

- **File:** `tradingagents/services/market_signals.py` — same file as 11.2 (market top detector), colocated market signals
- **O'Neil methodology:** FTD is a confirmed rally signal, not a prediction. Day count starts from first up day, not the low itself.
- **Stateless function design:** Caller passes full price/volume history, function derives state from data

### Key Design Decisions

- SPY used as primary instrument (broad market proxy, high liquidity, minimal tracking error)
- Quality score rewards stronger FTDs: bigger gains and higher volume = higher quality
- Day 4 is minimum — O'Neil historically noted days 4-7 produce the most reliable FTDs
- Function accepts pre-fetched data, no internal API calls

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Completion Notes List

- Added `detect_ftd()` to `tradingagents/services/market_signals.py` with full state machine: NO_CORRECTION -> CORRECTING -> RALLY_ATTEMPT -> FTD_CONFIRMED.
- FTD requires day 4+ of rally, >1.5% gain, above 50-day average volume.
- Quality score 0-100 based on gain magnitude and volume ratio.
- Dual tracking via SPY as primary instrument.
- State resets after sustained recovery above correction highs.

### File List

- `tradingagents/services/market_signals.py` (MODIFIED: added detect_ftd function)
