# Story 16.1: Compute AbnormalIV and MAX_EA Metrics

Status: ready-for-dev

## Story

As a trader,
I want the system to compute Expected Announcement Volatility metrics for any ticker with upcoming earnings,
so that I can identify which earnings events have the fattest option premiums relative to likely moves.

## Acceptance Criteria

1. **Given** a ticker has an upcoming earnings announcement and options chain data is available, **When** the EAV computation runs, **Then** AbnormalIV is calculated as: `(IV_30 - IV_60) / (1/30 - 1/60)` using ATM implied variances at ~30-day and ~60-day expirations

2. MAX_EA is calculated as: `max(|return_i|)` for the last 20 quarterly earnings announcements using historical price data

3. Both metrics are returned alongside the earnings date and ticker

4. When only one expiration is available (can't compute AbnormalIV), MAX_EA is used as the sole proxy

5. When historical earnings dates are unavailable for MAX_EA, the function returns None for that metric with a warning

6. The computation works entirely with yfinance data (options chains + historical prices)

7. Unit tests verify both metrics against hand-calculated examples

## Tasks / Subtasks

- [ ] Task 1: Create EAV computation service (AC: #1, #2, #3, #6)
  - [ ] 1.1 Create `tradingagents/services/earnings_volatility.py` with module docstring citing de Silva, So & Smith (2026)
  - [ ] 1.2 Create `EAVResult` dataclass with fields: ticker, earnings_date, abnormal_iv (Optional[float]), max_ea (Optional[float]), iv_30 (Optional[float]), iv_60 (Optional[float])
  - [ ] 1.3 Implement `compute_abnormal_iv(ticker)`: fetch options chain, find ATM options at ~30-day and ~60-day expirations, compute AbnormalIV = (IV_30 - IV_60) / (1/30 - 1/60)
  - [ ] 1.4 Implement `compute_max_ea(ticker)`: fetch historical price data, find past earnings dates via yfinance `.earnings_dates` or `.calendar`, compute max(|return|) around each earnings date
  - [ ] 1.5 Implement `compute_eav(ticker) -> EAVResult` that calls both and returns combined result
  - [ ] 1.6 For AbnormalIV: find ATM options by selecting strikes closest to spot price at each expiry bucket

- [ ] Task 2: Handle edge cases and fallbacks (AC: #4, #5)
  - [ ] 2.1 When only one expiration available: skip AbnormalIV (set to None), compute MAX_EA only
  - [ ] 2.2 When yfinance `.earnings_dates` is unavailable: try `.calendar` as fallback, then return None for MAX_EA with log warning
  - [ ] 2.3 When historical price data missing around an earnings date: skip that date in MAX_EA calculation
  - [ ] 2.4 When ticker has no options at all: return None for both metrics
  - [ ] 2.5 Guard against division by zero in AbnormalIV denominator (1/30 - 1/60 is constant ~0.0167, but guard anyway)

- [ ] Task 3: Write comprehensive unit tests (AC: #7)
  - [ ] 3.1 Create `tests/services/test_earnings_volatility.py`
  - [ ] 3.2 Test AbnormalIV with mocked options chain: known IV_30=0.40, IV_60=0.30 → expected AbnormalIV = (0.16 - 0.09) / (1/30 - 1/60) = 0.07 / 0.01667 ≈ 4.20 (using variances, not vols)
  - [ ] 3.3 Test MAX_EA with mocked earnings history: known returns [0.05, -0.08, 0.03, 0.12] → expected MAX_EA = 0.12
  - [ ] 3.4 Test single-expiration fallback: AbnormalIV=None, MAX_EA computed
  - [ ] 3.5 Test no-earnings-data: MAX_EA=None with warning
  - [ ] 3.6 Test no-options: both metrics None
  - [ ] 3.7 Test EAVResult dataclass has all expected fields
  - [ ] 3.8 Run existing tests to verify no regressions

## Dev Notes

### Architecture Pattern
- New service file: `tradingagents/services/earnings_volatility.py`
- Follow same pattern as `borrow_fee.py` and `microstructure.py`: dataclass + pure computation + yfinance helper
- Tests in `tests/services/test_earnings_volatility.py`

### Critical Implementation Details
- **Source**: de Silva, So & Smith (2026), "Losing is Optional" [losing_optional.pdf]
- **AbnormalIV formula**: Uses implied VARIANCES (IV squared), not raw IV: `(IV_30² - IV_60²) / (1/30 - 1/60)`
- **ATM definition**: Strike closest to current spot price
- **30-day / 60-day**: Find expirations closest to 30 and 60 DTE respectively
- **MAX_EA**: Maximum absolute return on the day of/after earnings over last 20 quarters (~5 years)
- **yfinance earnings**: `yf.Ticker(symbol).earnings_dates` returns past + upcoming earnings dates; `.calendar` has next earnings date

### Data Sources (yfinance)
- Options chain: `yf.Ticker(symbol).option_chain(expiry)` → calls/puts DataFrames with `impliedVolatility` column
- Expirations: `yf.Ticker(symbol).options` → list of expiry date strings
- Earnings dates: `yf.Ticker(symbol).earnings_dates` → DataFrame with past earnings
- Historical prices: `yf.Ticker(symbol).history(period="5y")` → for computing returns around earnings

### References
- [Source: wiki/app-notes/earnings-screener-enhancement.md] — EAV implementation approach
- [Source: wiki/strategies/fade-retail-earnings-options.md] — strategy context
- [Source: wiki/concepts/expected-announcement-volatility.md] — EAV concept
- [Source: knowledgebase/losing_optional.pdf] — original paper

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

### Change Log
