# Phase 1: Options Data Infrastructure - Research

**Researched:** 2026-03-31
**Domain:** Tradier REST API client, yfinance options fallback, vendor abstraction layer extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — all implementation choices are at Claude's discretion per CONTEXT.md.

### Claude's Discretion
All implementation choices. Key constraints to respect:
- Follow the existing Alpha Vantage client pattern (`requests`-based, in `tradingagents/dataflows/`)
- New file: `tradingagents/dataflows/tradier_utils.py`
- Add `options_data` category to `VENDOR_METHODS` in `interface.py`
- New config keys in `DEFAULT_CONFIG`: `enable_options`, `options_vendor`, `options_delta_target`, `options_dte_window`, `options_min_oi`
- Tradier API key via `TRADIER_API_KEY` env var
- Options chain response must include: strike, expiry, bid, ask, volume, OI, delta, gamma, theta, vega, IV per contract
- Historical IV must cover at least 52-week window

### Deferred Ideas (OUT OF SCOPE)
None stated.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Tradier API client integrated using existing `requests`-based pattern (same as Alpha Vantage) | Tradier uses Bearer token in Authorization header; `requests.get()` with `headers` and `params` matches existing pattern exactly |
| DATA-02 | Options chain data retrievable per ticker: strikes, expiries, bid/ask, volume, open interest, greeks (delta, gamma, theta, vega), IV per contract | Tradier `/markets/options/chains?greeks=true` returns all required fields; yfinance fallback has IV but no greeks |
| DATA-03 | Options vendor abstraction layer added to `interface.py` using existing `VENDOR_METHODS` routing pattern with a new `options_data` category | `TOOLS_CATEGORIES` + `VENDOR_METHODS` extension pattern is well-understood from reading interface.py |
| DATA-04 | Tradier API key configured via `.env` and `DEFAULT_CONFIG` | Pattern established: `os.getenv("TRADIER_API_KEY")` at call time; new keys added to `DEFAULT_CONFIG` dict |
| DATA-05 | Historical IV data retrievable per ticker over 52-week window | Tradier `/markets/history` returns OHLCV only — no direct IV. Strategy: collect ATM `smv_vol` from weekly options chain snapshots OR use yfinance `impliedVolatility` across expirations to build the 52-week series. Researched in detail below. |
</phase_requirements>

---

## Summary

This phase builds a Tradier REST API client and wires it into the existing `VENDOR_METHODS` routing system in `interface.py`. The codebase already has a clean, well-understood pattern from Alpha Vantage: a `_common.py` module defines the typed exception and the request helper; a feature-specific module (e.g., `alpha_vantage_stock.py`) holds the domain functions; and `interface.py` routes through `VENDOR_METHODS`. The Tradier implementation follows this structure exactly.

Tradier's options chain endpoint (`GET /v1/markets/options/chains`) returns a fully-populated response including `strike`, `expiration_date`, `option_type`, `bid`, `ask`, `volume`, `open_interest`, and a `greeks` sub-object with `delta`, `gamma`, `theta`, `vega`, `rho`, `phi`, `bid_iv`, `mid_iv`, `ask_iv`, and `smv_vol` (a smoothed IV value from ORATS). This satisfies DATA-02 completely with a single endpoint call. Authentication uses a static Bearer token, not OAuth — the `TRADIER_API_KEY` env var is read at call time and placed in the `Authorization: Bearer` header, exactly mirroring how Alpha Vantage reads `ALPHA_VANTAGE_API_KEY`.

For DATA-05 (historical IV), Tradier's `/markets/history` returns OHLCV only — there is no direct historical IV endpoint. The practical approach is to use the `smv_vol` field (ORATS smoothed IV, present in each chain snapshot) and build a 52-week rolling window by fetching weekly ATM chain snapshots. Because the project already uses a filesystem cache (`yfinance_cache.py`), these snapshots can be accumulated cheaply and the IV series assembled offline. The yfinance fallback path uses `ticker.option_chain(date).calls["impliedVolatility"]` across available expirations to approximate the same signal.

**Primary recommendation:** Model `tradier_utils.py` directly on `alpha_vantage_stock.py`; add a `TradierRateLimitError` exception; add `options_data` as a new `TOOLS_CATEGORIES` entry; register three `VENDOR_METHODS` entries (`get_options_expirations`, `get_options_chain`, `get_historical_iv`); add the five new keys to `DEFAULT_CONFIG`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | >=2.32.3 (already installed) | HTTP client for Tradier REST calls | Already in pyproject.toml; all existing vendor modules use it |
| `pandas` | >=2.3.0 (already installed) | DataFrame construction from JSON option chains | Already in pyproject.toml; used throughout dataflows |
| `yfinance` | >=0.2.63 (already installed) | Fallback options chain data | Already the default vendor; `ticker.options` + `ticker.option_chain()` give expirations + chain |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-dotenv` | already in requirements.txt | Load `.env` at startup | `TRADIER_API_KEY` must be in `.env` for local dev |

No new dependencies are required for this phase. The `requests` + `pandas` stack covers everything.

**Installation:**
No new packages. All required libraries are already declared in `pyproject.toml`.

**Version verification (confirmed):**
- `requests` 2.32.3 confirmed installed in base environment
- `pandas` >=2.3.0 declared in pyproject.toml
- `yfinance` >=0.2.63 declared in pyproject.toml

---

## Architecture Patterns

### Recommended Project Structure (new files only)
```
tradingagents/dataflows/
├── tradier_utils.py         # NEW: Tradier client (mirrors alpha_vantage_stock.py)
tradingagents/
├── default_config.py        # MODIFIED: add 5 new keys
tradingagents/dataflows/
├── interface.py             # MODIFIED: new TOOLS_CATEGORIES entry + 3 VENDOR_METHODS entries
```

### Pattern 1: Tradier Client Module (mirrors alpha_vantage_common + alpha_vantage_stock)

**What:** A single `tradier_utils.py` containing a typed exception, the API key getter, the request helper, and the three domain functions.

**When to use:** Always — keeps the pattern consistent with the Alpha Vantage split.

**The Alpha Vantage pattern (verified from source):**
```python
# alpha_vantage_common.py pattern to replicate:
API_BASE_URL = "https://www.alphavantage.co/query"

def get_api_key() -> str:
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is not set.")
    return api_key

class AlphaVantageRateLimitError(Exception):
    """Exception raised when Alpha Vantage API rate limit is exceeded."""
    pass

def _make_api_request(function_name: str, params: dict) -> dict | str:
    # ... builds params, calls requests.get(), checks for rate limit, returns text
```

**The Tradier equivalent:**
```python
# tradier_utils.py
import os
import requests
import pandas as pd
from datetime import datetime, timedelta

TRADIER_PRODUCTION_URL = "https://api.tradier.com/v1"
TRADIER_SANDBOX_URL    = "https://sandbox.tradier.com/v1"

class TradierRateLimitError(Exception):
    """Exception raised when Tradier API rate limit (429) is exceeded."""
    pass

def _get_api_key() -> str:
    api_key = os.getenv("TRADIER_API_KEY")
    if not api_key:
        raise ValueError("TRADIER_API_KEY environment variable is not set.")
    return api_key

def _get_base_url() -> str:
    """Return sandbox or production URL based on env var."""
    sandbox = os.getenv("TRADIER_SANDBOX", "false").lower() == "true"
    return TRADIER_SANDBOX_URL if sandbox else TRADIER_PRODUCTION_URL

def _make_request(endpoint: str, params: dict) -> dict:
    """Make authenticated GET request to Tradier API.

    Raises:
        TradierRateLimitError: When HTTP 429 is returned.
    """
    headers = {
        "Authorization": f"Bearer {_get_api_key()}",
        "Accept": "application/json",
    }
    url = f"{_get_base_url()}{endpoint}"
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 429:
        raise TradierRateLimitError(
            f"Tradier rate limit exceeded. "
            f"Available: {response.headers.get('X-Ratelimit-Available', 'unknown')}"
        )
    response.raise_for_status()
    return response.json()
```

### Pattern 2: Domain Functions

**What:** Three functions in `tradier_utils.py` — `get_options_expirations`, `get_options_chain`, `get_historical_iv`.

**Tradier endpoint reference (HIGH confidence, verified from official docs):**

| Function | Endpoint | Key Params |
|----------|----------|-----------|
| `get_options_expirations` | `GET /markets/options/expirations` | `symbol`, `includeAllRoots=true` |
| `get_options_chain` | `GET /markets/options/chains` | `symbol`, `expiration` (YYYY-MM-DD), `greeks=true` |
| `get_historical_iv` | derived — see DATA-05 strategy | — |

**get_options_chain response structure (verified from official Tradier docs):**
```json
{
  "options": {
    "option": [
      {
        "symbol": "AAPL260117C00150000",
        "description": "AAPL Jan 17 2026 $150.00 Call",
        "option_type": "call",
        "strike": 150.0,
        "expiration_date": "2026-01-17",
        "bid": 12.50,
        "ask": 12.75,
        "volume": 1234,
        "open_interest": 5678,
        "underlying": "AAPL",
        "greeks": {
          "delta": 0.72,
          "gamma": 0.015,
          "theta": -0.045,
          "vega": 0.22,
          "rho": 0.08,
          "phi": -0.06,
          "bid_iv": 0.28,
          "mid_iv": 0.285,
          "ask_iv": 0.29,
          "smv_vol": 0.2831,
          "updated_at": "2026-01-10T14:30:00"
        }
      }
    ]
  }
}
```

**get_options_expirations response structure:**
```json
{
  "expirations": {
    "date": [
      "2026-01-17",
      "2026-02-21",
      "2026-03-21"
    ]
  }
}
```

### Pattern 3: Historical IV Strategy (DATA-05)

**What:** Build a 52-week IV series by extracting ATM `smv_vol` from weekly chain snapshots.

**Why not use `/markets/history`:** That endpoint returns OHLCV only — no IV field. Confirmed from official docs. (LOW confidence that any single endpoint provides 52-week historical IV directly.)

**Practical approach (MEDIUM confidence):**

1. `get_historical_iv(symbol, start_date, end_date)` fetches the list of expirations.
2. For each expiration within the 52-week window, it fetches the chain for the nearest-dated expiration.
3. From each chain, it extracts the ATM contract's `smv_vol` (ORATS smoothed IV), which is the closest available proxy for the "daily IV" series.
4. Returns a pandas DataFrame with `(date, iv)` pairs suitable for IV rank / IV percentile computation.
5. The result is cached via `yfinance_cache.get_cached_dataframe()` with a 6-hour TTL.

**yfinance fallback for historical IV:**
```python
# yfinance fallback (MEDIUM confidence — no greeks, but impliedVolatility is present)
ticker = yf.Ticker(symbol.upper())
expirations = ticker.options   # tuple of date strings "YYYY-MM-DD"
for exp in expirations:
    chain = ticker.option_chain(exp)
    atm_iv = chain.calls["impliedVolatility"].median()  # ATM proxy
    # accumulate (exp, atm_iv) pairs
```

**yfinance options fields (confirmed from multiple sources):**
- `contractSymbol`, `lastTradeDate`, `strike`, `lastPrice`, `bid`, `ask`
- `change`, `percentChange`, `volume`, `openInterest`
- `impliedVolatility` (decimal, e.g. 0.25 for 25%)
- `inTheMoney`, `contractSize`, `currency`
- **No greeks** — delta/gamma/theta/vega NOT available from yfinance

### Pattern 4: VENDOR_METHODS Extension

**What:** Add new entries to `TOOLS_CATEGORIES` and `VENDOR_METHODS` in `interface.py`, then import the fallback from the yfinance options helper.

**Extension pattern (verified from interface.py source):**
```python
# interface.py additions

# 1. Import new functions
from .tradier_utils import (
    get_options_expirations as get_tradier_options_expirations,
    get_options_chain as get_tradier_options_chain,
    get_historical_iv as get_tradier_historical_iv,
)
from .tradier_utils import TradierRateLimitError
from .y_finance_options import (   # new helper module
    get_options_expirations as get_yfinance_options_expirations,
    get_options_chain as get_yfinance_options_chain,
    get_historical_iv as get_yfinance_historical_iv,
)

# 2. Add to VENDOR_LIST
VENDOR_LIST = ["yfinance", "alpha_vantage", "tradier"]  # add "tradier"

# 3. New TOOLS_CATEGORIES entry
TOOLS_CATEGORIES["options_data"] = {
    "description": "Options chain, expirations, and historical IV",
    "tools": ["get_options_expirations", "get_options_chain", "get_historical_iv"],
}

# 4. New VENDOR_METHODS entries
VENDOR_METHODS["get_options_expirations"] = {
    "tradier": get_tradier_options_expirations,
    "yfinance": get_yfinance_options_expirations,
}
VENDOR_METHODS["get_options_chain"] = {
    "tradier": get_tradier_options_chain,
    "yfinance": get_yfinance_options_chain,
}
VENDOR_METHODS["get_historical_iv"] = {
    "tradier": get_tradier_historical_iv,
    "yfinance": get_yfinance_historical_iv,
}
```

**Fallback chain behavior (from route_to_vendor in interface.py):**
The existing `route_to_vendor` function already handles fallback: it catches any `AlphaVantageRateLimitError` and continues to next vendor. The same logic must apply to `TradierRateLimitError`. The exception catch in `route_to_vendor` currently catches only `AlphaVantageRateLimitError` — it must be extended to also catch `TradierRateLimitError`. This is a one-line change to the except clause.

### Pattern 5: DEFAULT_CONFIG Extension

**What:** Add five new keys to `DEFAULT_CONFIG` in `default_config.py`.

**Verified current structure (from source):**
```python
DEFAULT_CONFIG = {
    # ... existing keys ...
    "data_vendors": {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "technical_pattern": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
        # ADD:
        "options_data": "tradier",   # Tradier is primary; yfinance is fallback
    },
    # ADD new top-level keys:
    "enable_options": False,          # Off by default — additive, non-breaking
    "options_vendor": "tradier",      # Primary vendor for options
    "options_delta_target": 0.30,     # Target delta for contract selection (Phase 3)
    "options_dte_window": [21, 45],   # DTE range [min, max] for contract selection
    "options_min_oi": 100,            # Minimum open interest filter
}
```

### Anti-Patterns to Avoid

- **Import at module level:** Do NOT import `TRADIER_API_KEY` at module load time. Read it inside `_get_api_key()` at call time — the existing Alpha Vantage pattern does this correctly, and it is the established convention.
- **Mixing Tradier+yfinance options data:** The yfinance fallback for options has NO greeks. Code that consumes the response must handle the case where the `greeks` key is absent (yfinance path returns a DataFrame without greeks). Return a consistent dict format; mark greeks as `None` when unavailable.
- **Single-expiration chain for historical IV:** Fetching a single chain snapshot is not historical IV. Must iterate across multiple past expirations or accumulate snapshots to get the 52-week window.
- **Hardcoding production URL:** Use env var `TRADIER_SANDBOX` to switch between sandbox and production so tests work without a production key.
- **Catching all exceptions as rate limit:** Only HTTP 429 is a rate limit signal. Do not treat other HTTP errors (404 invalid symbol, 401 bad key) as rate limit errors — raise them normally so the caller gets a useful error message.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client | Custom socket/urllib code | `requests` (already installed) | Already the project standard; error handling, retries, headers all built in |
| JSON parsing | Manual string manipulation | `response.json()` | requests handles Content-Type and encoding correctly |
| DataFrame construction | Manual dict loops | `pd.DataFrame(options_list)` | Pandas handles type coercion, None values, column alignment |
| Filesystem cache | Custom file-based caching | `yfinance_cache.get_cached_text()` / `get_cached_dataframe()` | Already implemented with SHA-256 keying and mtime-based TTL |
| IV computation from option prices | Black-Scholes solver | Tradier `smv_vol` from ORATS (already in chain response) | ORATS provides smoothed IV per contract; no computation needed for Phase 1 |

**Key insight:** The cache infrastructure is already there — `yfinance_cache.py` is fully general (prefix + payload dict + TTL + fetcher callable). All Tradier responses that should be cached can reuse it directly.

---

## Common Pitfalls

### Pitfall 1: Greeks Null in Sandbox
**What goes wrong:** Tradier's sandbox environment serves delayed data but does NOT include Greeks from ORATS. The `greeks` key in chain response will be `null` or absent when using a sandbox token.
**Why it happens:** Greeks are real-time data courtesy of ORATS and are not included in delayed/sandbox responses per Tradier's documented market data tiers.
**How to avoid:** Always `None`-check the `greeks` field. When greeks is null, log a warning rather than raising an exception. The production token will return greeks.
**Warning signs:** Chain response has `"greeks": null` on every contract — indicates sandbox mode.

### Pitfall 2: Single-Contract Response vs Array
**What goes wrong:** When only one option contract matches the query, Tradier may return the `option` field as a single object `{}` instead of a list `[{}]`. This breaks `pd.DataFrame(response["options"]["option"])`.
**Why it happens:** Tradier's JSON serializer omits the list wrapper for single-element collections in some endpoints. This is a documented quirk of their API design.
**How to avoid:** Always normalize: `options = data["options"]["option"]` → `if isinstance(options, dict): options = [options]`.
**Warning signs:** `TypeError: 'dict' object is not iterable` when constructing DataFrame from a response that worked for liquid tickers.

### Pitfall 3: Expirations Endpoint Returns Empty for Some Symbols
**What goes wrong:** Some symbols (indices, ETFs, less liquid stocks) return `{"expirations": null}` or `{"expirations": {"date": null}}`.
**Why it happens:** No listed options exist for that symbol on Tradier.
**How to avoid:** Null-check `data.get("expirations")` and the nested `date` field. Return an empty list `[]` rather than crashing. The caller should then fall back to yfinance.
**Warning signs:** `TypeError: 'NoneType' object is not iterable` when iterating dates.

### Pitfall 4: route_to_vendor Only Catches AlphaVantageRateLimitError
**What goes wrong:** `route_to_vendor` in `interface.py` has a hardcoded except clause for `AlphaVantageRateLimitError`. Without modification, a `TradierRateLimitError` will propagate as an unhandled exception and break the fallback chain.
**Why it happens:** The existing code was written before Tradier was added; its fallback logic is vendor-specific.
**How to avoid:** Modify the except clause in `route_to_vendor` to: `except (AlphaVantageRateLimitError, TradierRateLimitError): continue`.
**Warning signs:** Rate limit exceptions from Tradier crash the analysis instead of falling back to yfinance.

### Pitfall 5: Historical IV Requires Accumulation — Cannot Be Fetched in One Call
**What goes wrong:** Assuming there's a single endpoint that returns 52 weeks of daily IV. There is no such endpoint in Tradier (confirmed from docs).
**Why it happens:** Tradier provides real-time and current chain data; historical options snapshots are not in their free API.
**How to avoid:** Implement `get_historical_iv` to iterate available expirations from `get_options_expirations`, fetch each chain, extract ATM `smv_vol`, and assemble the series. Cache aggressively. For the first call, the series may be shorter than 52 weeks and grow over time. Accept this gracefully — agents downstream must handle partial series.
**Warning signs:** Fetching >50 chains in a single call; rate limit hit on the initial historical IV fetch.

### Pitfall 6: TRADIER_SANDBOX env var Not Set → Production Calls in Dev
**What goes wrong:** If `TRADIER_SANDBOX` is not set, the client defaults to `api.tradier.com` (production). Using a sandbox token against the production URL returns 401.
**Why it happens:** The two environments use different base URLs AND different tokens.
**How to avoid:** Make `_get_base_url()` default to sandbox when no env var is set (safer default for development). Document in `.env.example` that `TRADIER_SANDBOX=true` is the dev default.
**Warning signs:** HTTP 401 errors even though the API key is set.

---

## Code Examples

### 1. Tradier Authentication Pattern (verified)
```python
# Source: https://docs.tradier.com/docs/getting-started
headers = {
    "Authorization": f"Bearer {os.getenv('TRADIER_API_KEY')}",
    "Accept": "application/json",
}
response = requests.get(url, params=params, headers=headers)
```

### 2. Options Chain Fetch with Greeks (verified)
```python
# Source: https://docs.tradier.com/reference/brokerage-api-markets-get-options-chains
params = {
    "symbol": "AAPL",
    "expiration": "2026-01-17",
    "greeks": "true",
}
response = requests.get(
    "https://api.tradier.com/v1/markets/options/chains",
    params=params,
    headers={"Authorization": "Bearer <TOKEN>", "Accept": "application/json"},
)
data = response.json()
options = data["options"]["option"]
if isinstance(options, dict):
    options = [options]  # single-contract normalization
df = pd.DataFrame(options)
```

### 3. Options Expirations Fetch (verified)
```python
# Source: https://docs.tradier.com/reference/brokerage-api-markets-get-options-expirations
params = {
    "symbol": "AAPL",
    "includeAllRoots": "true",
}
data = _make_request("/markets/options/expirations", params)
expirations = data.get("expirations") or {}
dates = expirations.get("date") or []
if isinstance(dates, str):
    dates = [dates]  # single date edge case
```

### 4. yfinance Options Chain Fallback (verified from multiple sources)
```python
# Source: yfinance library documentation, multiple verified sources
ticker = yf.Ticker(symbol.upper())
# Get available expiration dates
expirations = ticker.options  # tuple of "YYYY-MM-DD" strings

# Get chain for specific expiration
chain = ticker.option_chain(expiration_date)
calls_df = chain.calls   # DataFrame columns: contractSymbol, lastTradeDate, strike,
                          # lastPrice, bid, ask, change, percentChange, volume,
                          # openInterest, impliedVolatility, inTheMoney,
                          # contractSize, currency
puts_df  = chain.puts    # same columns

# NOTE: No greeks in yfinance — delta/gamma/theta/vega all absent
# impliedVolatility is available (decimal, e.g. 0.25 for 25%)
```

### 5. Cache Pattern (verified from yfinance_cache.py source)
```python
# Reuse existing cache infrastructure
from .yfinance_cache import get_cached_text, get_cached_dataframe

OPTIONS_CHAIN_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours (same as market data)
HISTORICAL_IV_CACHE_TTL_SECONDS = 6 * 60 * 60

def get_options_chain(symbol: str, expiration: str) -> str:
    def _fetch() -> str:
        data = _make_request("/markets/options/chains", {
            "symbol": symbol.upper(),
            "expiration": expiration,
            "greeks": "true",
        })
        # ... parse and format ...
        return formatted_str

    return get_cached_text(
        prefix="options_chain",
        payload={"symbol": symbol.upper(), "expiration": expiration},
        max_age_seconds=OPTIONS_CHAIN_CACHE_TTL_SECONDS,
        fetcher=_fetch,
    )
```

### 6. Extending route_to_vendor for Tradier (verified from interface.py source)
```python
# Current interface.py line 169:
#   except AlphaVantageRateLimitError:
#       continue
#
# Modified to also catch Tradier:
except (AlphaVantageRateLimitError, TradierRateLimitError):
    continue
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fetching options greeks manually via Black-Scholes | Tradier provides greeks pre-computed via ORATS | Current | No B-S solver needed in Phase 1; use Tradier greeks directly |
| Historical IV from dedicated IV data vendor | Accumulate ATM smv_vol from chain snapshots | Ongoing pattern | Requires caching strategy; no single-call historical IV from free Tradier tier |

**Deprecated/outdated:**
- Historical IV via Tradier `/markets/history`: That endpoint returns OHLCV for equities only. Not useful for IV. This is confirmed.

---

## Open Questions

1. **Does Tradier sandbox return any greeks at all?**
   - What we know: Official docs state "No indices or Greeks" for sandbox. This suggests greeks are absent in sandbox.
   - What's unclear: Whether `smv_vol` specifically is available in sandbox (it comes from ORATS).
   - Recommendation: Implement greeks as optional (None-safe access). Test with production key; use sandbox for auth/request-structure tests only.

2. **HTTP status code for Tradier rate limit**
   - What we know: Tradier returns headers `X-Ratelimit-Available`, `X-Ratelimit-Used`, etc. Standard practice is 429. The Tradier docs do not explicitly state the status code for exceeded limits.
   - What's unclear: Whether Tradier returns 429 or a different code (200 with error body, like Alpha Vantage).
   - Recommendation: Handle both: check `response.status_code == 429` AND check for error in JSON body. LOW confidence on exact mechanism — needs empirical validation against live API.

3. **Scope of historical IV on first call**
   - What we know: The smv_vol-based historical IV strategy requires iterating expirations. A heavily-traded stock (AAPL, SPY) may have 50+ expirations within the 52-week window.
   - What's unclear: Whether fetching 50+ chains in sequence (at ~60 req/min sandbox) will be practical for initial load.
   - Recommendation: Limit initial fetch to weekly expirations only (not daily SPXW-style), reducing the count to ~52. Cache aggressively. Accept that on first call, the series builds incrementally.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.4 (installed in environment) |
| Config file | None detected — `pytest.ini` / `pyproject.toml [tool.pytest]` absent |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Tradier client makes authenticated GET with Bearer header | unit (mock requests) | `pytest tests/test_tradier_utils.py::test_auth_header -x` | ❌ Wave 0 |
| DATA-01 | TradierRateLimitError raised on 429 | unit (mock requests) | `pytest tests/test_tradier_utils.py::test_rate_limit_error -x` | ❌ Wave 0 |
| DATA-02 | get_options_chain returns DataFrame with required columns | unit (mock response) | `pytest tests/test_tradier_utils.py::test_options_chain_columns -x` | ❌ Wave 0 |
| DATA-02 | Single-contract normalization (dict→list) | unit | `pytest tests/test_tradier_utils.py::test_single_contract_normalization -x` | ❌ Wave 0 |
| DATA-03 | options_data category present in TOOLS_CATEGORIES | unit | `pytest tests/test_interface.py::test_options_data_category -x` | ❌ Wave 0 |
| DATA-03 | route_to_vendor falls back to yfinance on TradierRateLimitError | unit (mock) | `pytest tests/test_interface.py::test_tradier_fallback -x` | ❌ Wave 0 |
| DATA-04 | DEFAULT_CONFIG has all 5 new options keys | unit | `pytest tests/test_config.py::test_options_config_keys -x` | ❌ Wave 0 |
| DATA-05 | get_historical_iv returns DataFrame with (date, iv) columns | unit (mock) | `pytest tests/test_tradier_utils.py::test_historical_iv_columns -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_tradier_utils.py tests/test_interface.py tests/test_config.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — empty init for test package discovery
- [ ] `tests/test_tradier_utils.py` — covers DATA-01, DATA-02, DATA-05
- [ ] `tests/test_interface.py` — covers DATA-03 (routing/fallback)
- [ ] `tests/test_config.py` — covers DATA-04 (config keys)
- [ ] Framework config: add `[tool.pytest.ini_options] testpaths = ["tests"]` to `pyproject.toml`

---

## Sources

### Primary (HIGH confidence)
- `https://docs.tradier.com/reference/brokerage-api-markets-get-options-chains` — options chain endpoint, full response schema with greeks fields, request parameters
- `https://docs.tradier.com/reference/brokerage-api-markets-get-options-expirations` — expirations endpoint, response schema
- `https://docs.tradier.com/reference/brokerage-api-markets-get-history` — historical price endpoint; confirmed OHLCV only, no IV
- `https://docs.tradier.com/docs/rate-limiting` — rate limits (60/min sandbox, 120/min production), headers
- `https://docs.tradier.com/docs/getting-started` — Bearer token auth pattern, base URLs
- `tradingagents/dataflows/alpha_vantage_common.py` — source read directly; typed exception pattern
- `tradingagents/dataflows/alpha_vantage_stock.py` — source read directly; requests-based client pattern
- `tradingagents/dataflows/interface.py` — source read directly; VENDOR_METHODS routing pattern
- `tradingagents/dataflows/config.py` — source read directly; get_config() pattern
- `tradingagents/default_config.py` — source read directly; DEFAULT_CONFIG dict structure
- `tradingagents/dataflows/yfinance_cache.py` — source read directly; cache helper signatures

### Secondary (MEDIUM confidence)
- Multiple web sources confirming yfinance `ticker.option_chain()` columns: contractSymbol, strike, bid, ask, volume, openInterest, impliedVolatility — no greeks
- Python `requests` pattern for Tradier Bearer auth verified across multiple community tutorials

### Tertiary (LOW confidence)
- Tradier sandbox greeks absence — stated on market-data docs page but not definitively tested
- HTTP 429 as the Tradier rate limit status code — standard practice but not explicitly confirmed in Tradier rate-limit docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and verified in pyproject.toml
- Architecture: HIGH — client pattern verified from reading actual source files; Tradier endpoints verified from official docs
- Tradier greeks fields: HIGH — full response schema verified from official docs
- Historical IV strategy: MEDIUM — smv_vol is available in chain response (HIGH), but the 52-week accumulation strategy is inferred (no official historical IV endpoint confirmed absent, MEDIUM)
- Sandbox greeks behavior: LOW — stated in docs overview but not definitively confirmed with a live test
- Tradier 429 status code: LOW — assumed from HTTP standards; not confirmed in rate-limit doc

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (Tradier API is stable; yfinance interface may change faster)
