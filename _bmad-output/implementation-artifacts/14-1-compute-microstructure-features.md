# Story 14.1: Compute Microstructure Features from Daily OHLC

Status: review

## Story

As a trader,
I want the system to compute four microstructure variables from daily price data for any ticker,
so that the volatility analyst has quantitative inputs that capture market structure effects invisible to standard indicators.

## Acceptance Criteria

1. **Given** daily OHLC + Volume data is available for a ticker (at least 20 trading days), **When** the microstructure feature computation runs, **Then** it produces four variables:
   - **Range Volatility**: `(High - Low) / Open` — single-day volatility proxy
   - **Roll Measure**: `2 * sqrt(-cov(Delta_P_t, Delta_P_{t-1}))` — bid-ask spread proxy (returns 0 if covariance is positive)
   - **Price Impact**: `(1/T) * sum(|Delta_P| / V)` — price sensitivity to order flow
   - **Price Dispersion**: `sqrt(sum(w_t * (P_t - EP_t)^2))` — volume-weighted intraday price variability (approximated from OHLC)

2. All features are computed from daily OHLC data only (no tick data required, per AR-W2)

3. The function is located at `tradingagents/services/microstructure.py`

4. Features are returned as a dataclass with `ticker`, `date`, and the four float values

5. NaN/missing data is handled gracefully (returns None for individual features when insufficient data)

6. Unit tests verify computation against hand-calculated examples

## Tasks / Subtasks

- [x] Task 1: Validate and fix existing MicrostructureFeatures dataclass (AC: #3, #4)
  - [x] 1.1 Read existing `tradingagents/services/microstructure.py` — code was partially written in a prior session and may have issues
  - [x] 1.2 Verify `MicrostructureFeatures` dataclass has fields: `ticker`, `date`, `range_volatility`, `roll_measure`, `price_impact`, `price_dispersion` — all Optional[float]
  - [x] 1.3 Ensure `date` field is populated correctly (added `date` parameter to function signature)

- [x] Task 2: Validate and fix `compute_microstructure_features()` function (AC: #1, #2, #5)
  - [x] 2.1 Verify Range Volatility formula: `mean((High - Low) / Open)` — division by zero handled via np.where(opens > 0)
  - [x] 2.2 Verify Roll Measure formula: `2 * sqrt(-cov(deltaP_t, deltaP_{t-1}))` — uses np.cov, returns 0 when covariance positive
  - [x] 2.3 Verify Price Impact formula: `mean(|deltaP| / V)` — volume=0 rows excluded via valid_mask
  - [x] 2.4 Verify Price Dispersion formula: `sqrt(sum(w * (P - mean_P)^2))` — total_vol=0 returns None
  - [x] 2.5 Verify NaN/missing data handling: returns None for short data, individual features None when insufficient
  - [x] 2.6 Verify _fetch_ohlcv() returns [O,H,L,C,V] column order from yfinance

- [x] Task 3: Write comprehensive unit tests (AC: #6)
  - [x] 3.1 Create `tests/services/test_microstructure.py`
  - [x] 3.2 Test Range Volatility against hand-calculated example — verified with known OHLC fixtures
  - [x] 3.3 Test Roll Measure: negative cov → positive roll, positive cov → 0, hand-calculated formula match
  - [x] 3.4 Test Price Impact with known |deltaP|/V values + zero volume exclusion
  - [x] 3.5 Test Price Dispersion: hand-calc, constant price → 0, zero volume → None
  - [x] 3.6 Test insufficient data returns None (invalid ticker, <5 rows, empty array)
  - [x] 3.7 Test NaN in closes handled gracefully (no crash)
  - [x] 3.8 Test all four features + ticker + date present in dataclass
  - [x] 3.9 Full test suite run: 18/18 microstructure tests pass, 29 pre-existing failures unrelated

## Dev Notes

### Architecture Pattern
- Follow the same pattern as `tradingagents/services/borrow_fee.py` (most recent service added):
  - Module docstring with academic citation
  - Dataclass for output
  - Pure computation function (no side effects)
  - Optional yfinance fetch helper
  - Comprehensive unit tests in `tests/services/`

### Critical Implementation Details
- **Source**: Aldridge & Jiang (2024), "Managing Volatility for Profitable Options Trading" [ssrn-4953435.pdf]
- **Key finding**: OLS on these 4 features outperforms neural networks (AR-W3). Keep the implementation simple.
- **Data requirement**: Daily OHLC + Volume only (AR-W2). No tick data, no intraday feeds.
- **Price Dispersion approximation**: Since we don't have tick data, approximate using typical price `(H+L+C)/3` with volume-weighted variance. This is a standard OHLC-based proxy.

### Existing Code State
- `tradingagents/services/microstructure.py` already exists (265 lines) from a prior direct implementation attempt
- Contains both Story 14.1 (features) and Story 14.2 (OLS forecast) code
- **Must be validated against the ACs** — the prior attempt was not test-driven and may have bugs
- The `date` field on the dataclass is currently never populated
- The `_fetch_ohlcv()` helper exists but hasn't been tested

### Files to Touch
- `tradingagents/services/microstructure.py` — validate/fix existing code
- `tests/services/test_microstructure.py` — NEW: comprehensive test suite

### Testing Standards
- Use pytest with fixtures for synthetic OHLCV data
- Hand-calculate expected values for each formula to verify correctness
- Test edge cases: empty data, single row, zero volume, NaN values
- Run full test suite after to ensure no regressions

### Project Structure Notes
- Services live in `tradingagents/services/` — consistent with borrow_fee.py, breadth_scorer.py, regime_detector.py
- Tests in `tests/services/` — consistent with test_borrow_fee.py, test_market_calendar.py

### References
- [Source: wiki/app-notes/improve-volatility-analyst.md] — implementation approach and formulas
- [Source: wiki/concepts/microstructure-effects.md] — conceptual background
- [Source: knowledgebase/ssrn-4953435.pdf] — original paper by Aldridge & Jiang (2024)
- [Source: tradingagents/services/borrow_fee.py] — code pattern to follow

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- None — clean implementation, no debug cycles needed

### Completion Notes List
- Validated existing microstructure.py code against all 6 ACs — formulas correct
- Fixed: `date` parameter added to `compute_microstructure_features()` (was hardcoded "")
- Fixed: test for None ohlcv — function correctly falls through to yfinance fetch, not a bug
- All 4 formulas verified: Range Volatility, Roll Measure, Price Impact, Price Dispersion
- Edge cases covered: zero opens, zero volume, constant prices, NaN values, empty/short data
- 18 unit tests written and passing

### File List
- `tradingagents/services/microstructure.py` — MODIFIED (added `date` parameter)
- `tests/services/test_microstructure.py` — NEW (18 tests)

### Change Log
- 2026-04-16: Story 14.1 implemented — validated existing microstructure feature computation, added date parameter, wrote 18 comprehensive unit tests
