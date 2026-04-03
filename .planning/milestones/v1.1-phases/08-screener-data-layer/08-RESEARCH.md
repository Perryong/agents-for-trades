# Phase 8: Screener Data Layer - Research

**Researched:** 2026-04-02
**Domain:** yfinance bulk download, market session detection, in-memory caching, Pydantic v2 typed output, VENDOR_METHODS integration
**Confidence:** HIGH

## Summary

Phase 8 builds a pure Python data pipeline with no LLM involvement. It narrows the S&P 500 universe (~503 tickers) to 20-50 ranked candidates by fetching bulk OHLCV data via `yf.download`, computing three equal-weight signals (volume, momentum, unusual activity), and caching results by market session. All of this is encapsulated in a new `screener_data.py` module under `tradingagents/dataflows/` and wired into the existing `VENDOR_METHODS` / `TOOLS_CATEGORIES` / `DEFAULT_CONFIG` pattern with a new `screener_data` category.

The two key technical decisions made in CONTEXT.md that constrain implementation: (1) `exchange_calendars` for NYSE session detection — this library is NOT currently installed and must be added to `pyproject.toml`; (2) in-memory dict cache keyed by session date, not the existing CSV-based `yfinance_cache.py`. Both choices are sound and well-supported.

The biggest practical risk is yfinance HTTP 429 rate-limit errors on 500+ ticker downloads. Verified approach: chunk to 80-100 tickers per `yf.download` call, catch `yfinance.exceptions.YFRateLimitError`, apply exponential backoff (base 2s, jitter, cap at 60s), and track successful vs failed tickers for the coverage metric.

**Primary recommendation:** Implement `screener_data.py` with chunked `yf.download(group_by='ticker')`, `exchange_calendars` session boundary detection, an in-memory `dict` keyed by session date string, and a Pydantic v2 `ScreenerCandidate` model. Wire into `interface.py` exactly as `options_data` was wired in Phase 4.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Scan S&P 500 universe (~503 tickers) as the default market universe
- Equal-weight composite score: volume, momentum, unusual activity (1/3 each)
- Unusual activity = volume > 2x 20-day average AND price change > 1.5%
- Output: flat list of candidates sorted by composite score (not grouped by signal)
- Use `exchange_calendars` library for NYSE session detection (handles holidays, half-days, exact open/close)
- 15-minute TTL for cache during market hours
- In-memory dict cache keyed by session — resets on process restart, no stale disk files
- Partial fetch failures return available data plus a coverage metric; caller decides threshold
- Two new methods in VENDOR_METHODS: `get_screener_universe` (bulk OHLCV fetch) and `get_screener_signals` (volume/momentum/activity scoring)
- Reuse existing `route_to_vendor` fallback chain for consistency
- New module: `screener_data.py` in `tradingagents/dataflows/`
- Pydantic `ScreenerCandidate` model with ticker, scores, rank for typed output

### Claude's Discretion
- Chunking strategy for bulk yfinance fetch (80-100 per chunk with exponential backoff per STATE.md)
- Internal helper function organization within screener_data.py
- Exact momentum calculation window (e.g., 5-day vs 10-day returns)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCREEN-01 | Programmatic pre-filter scans market universe via yfinance bulk download with chunked fetching and rate-limit safety | `yf.download(group_by='ticker')` verified; `YFRateLimitError` exception class confirmed; chunk 80-100 tickers with exponential backoff |
| SCREEN-02 | Pre-filter outputs scored candidate list (max 50) ranked by volume, momentum, and unusual activity signals | Signal formulas verified in live yfinance data; composite score = mean of 3 min-max normalized scores |
| SCREEN-03 | Screener data routed through existing `VENDOR_METHODS` pattern with new `screener_data` category | `interface.py` pattern read directly; `TOOLS_CATEGORIES` and `DEFAULT_CONFIG` extension points identified |
| SCREEN-04 | Market-session-aware cache prevents stale data during trading hours and avoids unnecessary refetches after close | `exchange_calendars` 4.13.2 API verified; `is_trading_minute()` and `schedule` attrs confirmed; must be added to pyproject.toml |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| yfinance | 0.2.63 (installed) | Bulk OHLCV fetch via `yf.download` | Already project dependency; `YFRateLimitError` for clean retry handling |
| exchange-calendars | 4.13.2 (latest) | NYSE session boundary detection — holidays, half-days, early close | Only mature library with exact NYSE open/close minutes; pytz alone misses holidays and half-days |
| pydantic | 2.11.7 (installed) | `ScreenerCandidate` typed output model | Already project dependency; v2 `BaseModel` + `model_dump()` confirmed working |
| pandas | 2.3.0 (installed) | Bulk data manipulation, signal calculation | Already project dependency |
| pytz | 2025.2 (installed) | Timezone conversion support | Already project dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| yfinance.exceptions.YFRateLimitError | built-in | Rate-limit exception catch | Wrap each chunk download to trigger retry |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| exchange-calendars | pytz + weekday check only | pytz misses NYSE holidays (Good Friday, Juneteenth) and half-days (day-after-Thanksgiving); exchange_calendars is the correct choice per CONTEXT.md |
| in-memory dict cache | yfinance_cache.py CSV cache | CSV cache designed for single-ticker requests with content-hash keys; session-keyed screener results need a different eviction unit |
| yf.download group_by='ticker' | individual yf.Ticker().history() | Individual calls hit rate limits far faster; bulk download is the only viable path for 500 tickers |

**Installation (new dependency only):**
```bash
uv add exchange-calendars
```

**Version verification:** exchange-calendars 4.13.2 confirmed via `uv pip index versions exchange-calendars` (2026-04-02). All other packages already installed and verified.

---

## Architecture Patterns

### Recommended Project Structure
```
tradingagents/
├── dataflows/
│   ├── interface.py          # Add screener_data category + VENDOR_METHODS entries
│   ├── screener_data.py      # NEW: bulk fetch + scoring + session cache
│   └── (existing files unchanged)
└── default_config.py         # Add screener_data vendor config entry
tests/
└── dataflows/
    └── test_screener_data.py # NEW: unit tests for scoring + cache logic
```

### Pattern 1: Chunked Bulk Fetch with Exponential Backoff

**What:** Split the 503-ticker universe into chunks of 80-100. Call `yf.download` per chunk. Catch `YFRateLimitError` and retry with exponential backoff. Track which tickers succeeded vs failed.

**When to use:** Any time fetching 100+ tickers from yfinance.

**Example:**
```python
# Verified against yfinance 0.2.63, 2026-04-02
import time
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

CHUNK_SIZE = 90
MAX_RETRIES = 4
BACKOFF_BASE = 2.0  # seconds

def _fetch_chunk(tickers: list[str], period: str = "25d") -> dict[str, pd.DataFrame]:
    """
    Download a single chunk. Returns {ticker: DataFrame} for successful tickers.
    Uses group_by='ticker' so data[ticker] gives per-ticker OHLCV.
    period='25d' gives enough history for 20-day volume average + 5-day momentum.
    """
    attempt = 0
    while attempt <= MAX_RETRIES:
        try:
            raw = yf.download(
                tickers,
                period=period,
                auto_adjust=True,
                progress=False,
                group_by="ticker",
            )
            result = {}
            for ticker in tickers:
                try:
                    df = raw[ticker].dropna(how="all")
                    if not df.empty:
                        result[ticker] = df
                except (KeyError, TypeError):
                    pass  # Ticker missing from response — counted as failure
            return result
        except YFRateLimitError:
            if attempt == MAX_RETRIES:
                return {}  # All retries exhausted, return empty for this chunk
            wait = BACKOFF_BASE ** (attempt + 1)
            time.sleep(wait)
            attempt += 1
    return {}
```

### Pattern 2: Market Session Cache (in-memory dict)

**What:** Cache keyed by `(session_date_str, "screener")`. During a session, a 15-minute TTL prevents redundant fetches. After session close, cache is logically stale (old session key won't match new session date).

**When to use:** Session-scoped data where process restart = acceptable invalidation.

**Example:**
```python
# exchange_calendars API verified from official GitHub docs, 2026-04-02
import exchange_calendars as xcals
from datetime import datetime
import pytz

_SCREENER_CACHE: dict[str, tuple[list, float]] = {}  # key -> (results, timestamp)
_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes

_eastern = pytz.timezone("US/Eastern")
_xnys = xcals.get_calendar("XNYS")  # NYSE calendar; instantiate once at module level

def _get_session_key() -> str | None:
    """
    Returns today's session date string if market is open, else None.
    Uses exchange_calendars for holiday/half-day awareness.
    """
    now_et = datetime.now(_eastern)
    now_utc = now_et.astimezone(pytz.utc)
    now_ts = pd.Timestamp(now_utc)
    
    if _xnys.is_trading_minute(now_ts):
        return now_et.strftime("%Y-%m-%d")
    return None

def _cache_get(session_key: str) -> list | None:
    if session_key not in _SCREENER_CACHE:
        return None
    results, ts = _SCREENER_CACHE[session_key]
    if time.time() - ts > _CACHE_TTL_SECONDS:
        del _SCREENER_CACHE[session_key]
        return None
    return results

def _cache_set(session_key: str, results: list) -> None:
    _SCREENER_CACHE[session_key] = (results, time.time())
```

### Pattern 3: Signal Scoring with Min-Max Normalization

**What:** Compute three raw signals per ticker, then min-max normalize each to [0, 1] across all candidates before averaging into a composite score.

**When to use:** Any time signals are on different scales (volume ratios vs price returns vs binary flags).

**Example:**
```python
import pandas as pd
import numpy as np

def _compute_signals(universe_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Compute raw signals for all tickers. Returns DataFrame with columns:
    ticker, volume_ratio, momentum_5d, unusual_activity.
    """
    rows = []
    for ticker, df in universe_data.items():
        if len(df) < 21:  # Need 20-day avg + at least 1 current day
            continue
        
        current_vol = df["Volume"].iloc[-1]
        avg_20_vol = df["Volume"].iloc[-21:-1].mean()
        volume_ratio = current_vol / avg_20_vol if avg_20_vol > 0 else 0.0
        
        # 5-day momentum: recommended over 10-day for screener responsiveness
        if len(df) >= 6:
            momentum = (df["Close"].iloc[-1] - df["Close"].iloc[-6]) / df["Close"].iloc[-6]
        else:
            momentum = 0.0
        
        price_change_1d = (
            (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]
            if len(df) >= 2 else 0.0
        )
        unusual_activity = float(volume_ratio > 2.0 and abs(price_change_1d) > 0.015)
        
        rows.append({
            "ticker": ticker,
            "volume_ratio": volume_ratio,
            "momentum_5d": momentum,
            "unusual_activity": unusual_activity,
        })
    
    df_signals = pd.DataFrame(rows)
    
    # Min-max normalize each signal to [0, 1]
    for col in ["volume_ratio", "momentum_5d", "unusual_activity"]:
        col_min = df_signals[col].min()
        col_max = df_signals[col].max()
        rng = col_max - col_min
        df_signals[f"{col}_score"] = (
            (df_signals[col] - col_min) / rng if rng > 0 else 0.5
        )
    
    df_signals["composite_score"] = (
        df_signals["volume_ratio_score"]
        + df_signals["momentum_5d_score"]
        + df_signals["unusual_activity_score"]
    ) / 3.0
    
    return df_signals.sort_values("composite_score", ascending=False).reset_index(drop=True)
```

### Pattern 4: VENDOR_METHODS Integration (mirrors existing options_data pattern)

**What:** Two new entries in `VENDOR_METHODS`, one new entry in `TOOLS_CATEGORIES`, one new entry in `DEFAULT_CONFIG["data_vendors"]`. Import from `screener_data.py` with aliased names at top of `interface.py`.

**Example additions to interface.py:**
```python
# At top of interface.py (new import block)
from .screener_data import (
    get_screener_universe as get_yfinance_screener_universe,
    get_screener_signals as get_yfinance_screener_signals,
)

# In TOOLS_CATEGORIES
"screener_data": {
    "description": "Bulk market universe fetch and signal scoring for screener",
    "tools": [
        "get_screener_universe",
        "get_screener_signals",
    ],
},

# In VENDOR_METHODS
"get_screener_universe": {
    "yfinance": get_yfinance_screener_universe,
},
"get_screener_signals": {
    "yfinance": get_yfinance_screener_signals,
},
```

**Example addition to default_config.py:**
```python
# In DEFAULT_CONFIG["data_vendors"]
"screener_data": "yfinance",
```

### Pattern 5: Pydantic v2 ScreenerCandidate Model

**What:** Typed output model for each screener result. `model_dump()` for JSON serialization downstream.

**Example (verified against pydantic 2.11.7):**
```python
from pydantic import BaseModel
from typing import Optional

class ScreenerCandidate(BaseModel):
    ticker: str
    volume_score: float        # normalized [0, 1]
    momentum_score: float      # normalized [0, 1]
    unusual_activity_score: float  # normalized [0, 1]
    composite_score: float     # equal-weight mean of three scores
    rank: int                  # 1-indexed rank (1 = best)
    coverage_note: Optional[str] = None  # e.g. "503/503 tickers fetched"
```

### Anti-Patterns to Avoid

- **Calling `yf.Ticker(ticker).history()` in a loop for 500 tickers:** Each call is a separate HTTP request. Triggers rate limits within ~50 calls. Always use `yf.download(list_of_tickers)`.
- **Using `multi_level_index=False` with multiple tickers:** When `multi_level_index=False` is set, yfinance returns a flat column structure only for single-ticker downloads — with multiple tickers it still returns MultiIndex. Use `group_by='ticker'` and access `data[ticker]` instead.
- **Keying in-memory cache by wall-clock TTL alone:** A 15-minute TTL starting at 9:31 AM would expire at 9:46 AM, but a 15-minute TTL starting at 3:55 PM would still be "valid" at 9:30 AM next day. The session date key prevents cross-session pollution.
- **Instantiating `xcals.get_calendar("XNYS")` on every call:** Calendar objects are expensive to create (~200ms). Instantiate once at module level.
- **Placing the coverage threshold check inside `screener_data.py`:** The CONTEXT.md decision says "caller decides threshold." The module returns a coverage float (e.g., 0.87) and lets the caller reject or proceed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NYSE holiday/half-day detection | Custom list of NYSE holidays in code | `exchange_calendars` XNYS calendar | Holidays change yearly; Good Friday, Juneteenth, emergency closures (9/11) need a maintained source |
| Rate-limit handling | `requests` with manual HTTP status inspection | Catch `yfinance.exceptions.YFRateLimitError` | yfinance already wraps HTTP 429 into this exception; catching it is the documented retry pattern |
| Ticker universe maintenance | Hardcoded list of 503 tickers | `pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]["Symbol"]` | S&P 500 composition changes quarterly; scraping Wikipedia at fetch time gives current membership |
| Per-field validation on ScreenerCandidate | Manual type assertions | Pydantic v2 `BaseModel` | Already installed; runtime validation, JSON schema, `.model_dump()` all included |
| Dataframe signal normalization | Scipy min-max scaler import | Inline pandas arithmetic `(x - x.min()) / (x.max() - x.min())` | pandas is already imported; adding scipy for one normalization step is unnecessary overhead |

**Key insight:** The most expensive custom solutions in this domain are exchange calendar maintenance and rate-limit handling. Both have well-maintained solutions available in the ecosystem.

---

## Common Pitfalls

### Pitfall 1: Wikipedia Table Format Changes
**What goes wrong:** `pd.read_html` on the Wikipedia S&P 500 page returns the table but column names change (e.g., "Symbol" becomes "Ticker").
**Why it happens:** Wikipedia editors rename columns. The page structure is not a stable API.
**How to avoid:** Access column by index `[0]` for the Symbol column OR check both `"Symbol"` and `"Ticker"` with a fallback. Wrap in try/except and log column names if parse fails.
**Warning signs:** `KeyError: 'Symbol'` on the first `get_screener_universe` call.

### Pitfall 2: yf.download Silent Failures for Delisted/Invalid Tickers
**What goes wrong:** A ticker in the S&P 500 list is delisted or changed. `yf.download` silently omits it from the result without raising an exception.
**Why it happens:** yfinance swallows per-ticker errors in bulk download mode.
**How to avoid:** After the download, compute `len(universe_data) / len(requested_tickers)` as the coverage metric. This is the designed behavior — not a bug. The coverage metric surfaces it.
**Warning signs:** Coverage metric drops below 80% unexpectedly.

### Pitfall 3: Multi-Level Column Index Access with group_by='ticker'
**What goes wrong:** Code tries `raw["Close"]["AAPL"]` expecting column-first access, but `group_by='ticker'` returns ticker-first.
**Why it happens:** yfinance `group_by` default is `'column'`. Switching to `'ticker'` flips the MultiIndex levels.
**How to avoid:** Always use `raw[ticker]["Close"]` (ticker outer, OHLCV inner) when `group_by='ticker'`. Verified: `data["AAPL"]` returns a DataFrame with columns `["Close", "High", "Low", "Open", "Volume"]`.
**Warning signs:** `KeyError` on column access, or getting a Series when a DataFrame is expected.

### Pitfall 4: exchange_calendars `is_trading_minute` Requires Timezone-Aware Timestamp
**What goes wrong:** Passing a naive `pd.Timestamp` to `xnys.is_trading_minute()` raises a `ValueError` or returns incorrect results.
**Why it happens:** exchange_calendars stores session times in UTC internally. Naive timestamps are ambiguous.
**How to avoid:** Always convert to UTC-aware `pd.Timestamp` before calling: `pd.Timestamp(datetime.now(pytz.utc))`.
**Warning signs:** `TypeError: Cannot compare tz-naive and tz-aware datetime-like objects`

### Pitfall 5: In-Memory Cache Not Thread-Safe
**What goes wrong:** If `route_to_vendor("get_screener_universe")` is called concurrently (e.g., from a future async API endpoint), two coroutines may both find a cache miss and trigger simultaneous downloads.
**Why it happens:** Dict read/write in Python is atomic at the GIL level, but the check-then-set pattern is not atomic.
**How to avoid:** For Phase 8 (synchronous use only per CONTEXT.md), this is acceptable. Document a `threading.Lock` upgrade path for Phase 10 when the async API is built.
**Warning signs:** Duplicate simultaneous downloads in Phase 10 logs.

### Pitfall 6: Momentum Score Sign Inversion in Min-Max Normalization
**What goes wrong:** If all tickers have negative 5-day returns, min-max normalization maps the least-negative to 1.0 (highest score), which misrepresents the intent.
**Why it happens:** Min-max is scale-invariant and knows nothing about "higher is better."
**How to avoid:** This is acceptable behavior for a relative screener — the goal is ranking candidates relative to each other in the current scan, not against an absolute threshold. Document this clearly in the module docstring.
**Warning signs:** "Best picks" have strongly negative momentum during broad selloffs — this is expected, not a bug.

---

## Code Examples

### Bulk Download with Coverage Tracking
```python
# Verified pattern: yfinance 0.2.63, group_by='ticker', 2026-04-02
import yfinance as yf
import pandas as pd
import time
from yfinance.exceptions import YFRateLimitError

def fetch_universe_data(
    tickers: list[str],
    chunk_size: int = 90,
    max_retries: int = 4,
    backoff_base: float = 2.0,
) -> tuple[dict[str, pd.DataFrame], float]:
    """
    Returns (data_by_ticker, coverage_ratio).
    coverage_ratio = successful tickers / requested tickers.
    """
    all_data: dict[str, pd.DataFrame] = {}
    
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i : i + chunk_size]
        attempt = 0
        
        while attempt <= max_retries:
            try:
                raw = yf.download(
                    chunk,
                    period="25d",  # 20-day avg + 5-day momentum buffer
                    auto_adjust=True,
                    progress=False,
                    group_by="ticker",
                )
                for ticker in chunk:
                    try:
                        df = raw[ticker].dropna(how="all")
                        if not df.empty:
                            all_data[ticker] = df
                    except (KeyError, TypeError):
                        pass
                break  # Chunk succeeded
            except YFRateLimitError:
                if attempt == max_retries:
                    break  # Give up on this chunk, keep going with others
                wait = backoff_base ** (attempt + 1)
                time.sleep(wait)
                attempt += 1
    
    coverage = len(all_data) / len(tickers) if tickers else 0.0
    return all_data, coverage
```

### exchange_calendars Session Detection
```python
# Source: exchange_calendars GitHub README + verified API calls
import exchange_calendars as xcals
import pandas as pd
import pytz
from datetime import datetime

_xnys = xcals.get_calendar("XNYS")  # Module-level singleton
_eastern = pytz.timezone("US/Eastern")

def is_market_open() -> bool:
    """Returns True if NYSE is currently in a trading minute."""
    now_utc = pd.Timestamp(datetime.now(pytz.utc))
    return _xnys.is_trading_minute(now_utc)

def get_current_session_date() -> str | None:
    """Returns 'YYYY-MM-DD' if market is open today, None otherwise."""
    now_et = datetime.now(_eastern)
    now_utc = pd.Timestamp(datetime.now(pytz.utc))
    if _xnys.is_trading_minute(now_utc):
        return now_et.strftime("%Y-%m-%d")
    return None
```

### S&P 500 Ticker Universe Fetch
```python
# Source: Multiple community examples, verified approach 2026-04-02
import pandas as pd

def get_sp500_tickers() -> list[str]:
    """Fetch current S&P 500 tickers from Wikipedia."""
    try:
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"},  # Target the specific table by ID
        )
        df = tables[0]
        # Try both known column names for robustness
        symbol_col = "Symbol" if "Symbol" in df.columns else df.columns[0]
        tickers = df[symbol_col].str.replace(".", "-", regex=False).tolist()
        return tickers
    except Exception:
        raise RuntimeError("Failed to fetch S&P 500 ticker list from Wikipedia")
```

### ScreenerCandidate Model
```python
# Verified: pydantic 2.11.7, 2026-04-02
from pydantic import BaseModel
from typing import Optional

class ScreenerCandidate(BaseModel):
    ticker: str
    volume_score: float
    momentum_score: float
    unusual_activity_score: float
    composite_score: float
    rank: int
    coverage_note: Optional[str] = None

# Usage
candidate = ScreenerCandidate(
    ticker="NVDA",
    volume_score=0.92,
    momentum_score=0.78,
    unusual_activity_score=1.0,
    composite_score=0.90,
    rank=1,
    coverage_note="498/503 tickers fetched (99.0%)",
)
payload = candidate.model_dump()  # -> dict, ready for JSON or Phase 9 LLM input
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `yf.Ticker(t).history()` in loop | `yf.download([...], group_by='ticker')` | Post-2023 rate-limit tightening | Single bulk request vs N individual requests; required for 100+ tickers |
| Ignoring `multi_level_index` param | `group_by='ticker'` for per-ticker access | yfinance 0.2.x | Explicit column structure; `data[ticker]` returns clean OHLCV DataFrame |
| `except Exception` for rate limits | `except YFRateLimitError` | yfinance introduced typed exceptions | Clean retry logic; doesn't swallow unrelated errors |
| Pytz weekday check for "is market open" | `exchange_calendars` `is_trading_minute()` | exchange_calendars 4.x | Handles holidays, half-days, emergency closures correctly |

**Deprecated/outdated:**
- `trading_calendars` (Quantopian): Archived, superseded by `exchange_calendars` fork. Do not use.
- `pandas_market_calendars`: Alternative to `exchange_calendars`, also valid but not the locked decision.

---

## Open Questions

1. **Wikipedia table stability at parse time**
   - What we know: The `id="constituents"` HTML attribute has been stable for several years
   - What's unclear: No SLA on Wikipedia table structure
   - Recommendation: Use `attrs={"id": "constituents"}` for table targeting, add column name fallback (`"Symbol"` vs first column), wrap entire function in try/except with a descriptive RuntimeError

2. **Chunk size tuning (80-100)**
   - What we know: STATE.md documents 80-100 as the safe range based on post-2024 rate-limit behavior
   - What's unclear: Exact threshold — Yahoo Finance doesn't publish rate limits publicly
   - Recommendation: Default to 90 per chunk; make it a config parameter (`screener_chunk_size`) in DEFAULT_CONFIG so it can be tuned without code changes

3. **Momentum window: 5-day vs 10-day**
   - What we know: Both windows verified computationally; 5-day is more responsive to recent price action, 10-day is smoother
   - What's unclear: Which window produces better screener recall (no backtest data)
   - Recommendation: Use 5-day (`period="25d"` covers it comfortably with 20-day volume avg). Document as Claude's discretion choice. Config-parameterize if needed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (confirmed installed, 174 tests pass) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/dataflows/test_screener_data.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCREEN-01 | `fetch_universe_data` with mocked `yf.download` returns dict + coverage float | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_fetch_universe_returns_coverage -x` | Wave 0 |
| SCREEN-01 | `YFRateLimitError` triggers retry, does not propagate | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_rate_limit_retries -x` | Wave 0 |
| SCREEN-02 | `compute_screener_signals` returns list of `ScreenerCandidate` sorted by composite_score desc | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_scoring_returns_sorted_candidates -x` | Wave 0 |
| SCREEN-02 | Composite score = mean of 3 normalized sub-scores | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_composite_score_is_equal_weight_mean -x` | Wave 0 |
| SCREEN-02 | Unusual activity flag: volume_ratio > 2.0 AND price_change > 1.5% | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_unusual_activity_threshold -x` | Wave 0 |
| SCREEN-03 | `VENDOR_METHODS` has `get_screener_universe` and `get_screener_signals` keys | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_vendor_methods_has_screener_keys -x` | Wave 0 |
| SCREEN-03 | `TOOLS_CATEGORIES` has `screener_data` category | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_tools_categories_has_screener_data -x` | Wave 0 |
| SCREEN-03 | `route_to_vendor("get_screener_universe")` calls the yfinance implementation | unit (mock) | `uv run pytest tests/dataflows/test_screener_data.py::test_route_to_vendor_screener_universe -x` | Wave 0 |
| SCREEN-04 | Cache hit returns same object, no new `yf.download` call within 15-min TTL | unit (mock time) | `uv run pytest tests/dataflows/test_screener_data.py::test_cache_hit_within_ttl -x` | Wave 0 |
| SCREEN-04 | Cache miss after TTL expiry triggers fresh fetch | unit (mock time) | `uv run pytest tests/dataflows/test_screener_data.py::test_cache_miss_after_ttl -x` | Wave 0 |
| SCREEN-04 | Different session date key misses cache (cross-session isolation) | unit (mock datetime) | `uv run pytest tests/dataflows/test_screener_data.py::test_cache_isolates_by_session_date -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/dataflows/test_screener_data.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/dataflows/test_screener_data.py` — covers all SCREEN-01 through SCREEN-04 test IDs above (file does not exist yet)

---

## Sources

### Primary (HIGH confidence)
- `tradingagents/dataflows/interface.py` — VENDOR_METHODS, TOOLS_CATEGORIES, route_to_vendor pattern read directly from codebase
- `tradingagents/dataflows/yfinance_cache.py` — existing cache pattern (CSV-based; confirmed different from in-memory approach needed here)
- `tradingagents/default_config.py` — DEFAULT_CONFIG structure, data_vendors entries
- yfinance 0.2.63 live API — `yf.download` signature, `group_by='ticker'` behavior, `YFRateLimitError` exception class — all verified by running in project environment
- pydantic 2.11.7 — `BaseModel`, `model_dump()` — verified by running in project environment
- exchange_calendars GitHub README — `is_trading_minute()`, `get_calendar("XNYS")`, `session_minutes()` API confirmed

### Secondary (MEDIUM confidence)
- [exchange_calendars PyPI](https://pypi.org/project/exchange-calendars/) — version 4.13.2 confirmed as latest; dependency list (numpy, pandas, pyluach, toolz, tzdata, korean_lunar_calendar)
- [exchange_calendars GitHub](https://github.com/gerrymanoim/exchange_calendars) — API docs for `is_trading_minute`, `schedule`, `is_session`
- [yfinance GitHub issue #2125](https://github.com/ranaroussi/yfinance/issues/2125) — community confirmation of 429 rate-limit pattern and retry approach

### Tertiary (LOW confidence)
- WebSearch: chunk size 80-100 — documented in STATE.md as project decision; empirical tuning still needed
- WebSearch: Wikipedia S&P 500 table `id="constituents"` stability — not officially guaranteed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in live project environment; exchange_calendars verified via PyPI index
- Architecture: HIGH — VENDOR_METHODS/TOOLS_CATEGORIES pattern read directly from interface.py; signal formulas verified with live yfinance data
- Pitfalls: HIGH for yfinance-specific pitfalls (verified by running code); MEDIUM for Wikipedia table stability (community knowledge)
- Test map: HIGH — test commands match existing pytest infrastructure (174 tests passing)

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable ecosystem; yfinance rate-limit behavior could shift earlier if Yahoo changes policy)
