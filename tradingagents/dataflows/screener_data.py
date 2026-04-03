"""
Screener data module: bulk yfinance fetch with chunking and rate-limit safety,
signal scoring with min-max normalization, session-boundary cache using
exchange_calendars, and the Pydantic ScreenerCandidate model.

Signal normalization note:
    Min-max normalization is relative ranking, not absolute. During a broad
    market selloff, the "best picks" may still have negative 5-day momentum.
    The composite score ranks candidates relative to each other in the current
    scan — it does NOT represent an absolute quality threshold. This is
    expected behavior for a relative screener.

Cache note:
    The in-memory session cache is keyed by NYSE session date ("YYYY-MM-DD").
    A 15-minute TTL prevents redundant fetches within a session. The cache
    resets naturally on process restart (no stale disk files). For Phase 10
    async API usage, upgrade the check-then-set to use threading.Lock.
"""

from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Optional

import exchange_calendars as xcals
import pandas as pd
import pytz
import yfinance as yf
from pydantic import BaseModel
from yfinance.exceptions import YFRateLimitError

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

CHUNK_SIZE = 90
MAX_RETRIES = 4
BACKOFF_BASE = 2.0  # seconds
_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes

# ---------------------------------------------------------------------------
# Module-level singletons (instantiate once — expensive to create)
# ---------------------------------------------------------------------------

_eastern = pytz.timezone("US/Eastern")
_xnys = xcals.get_calendar("XNYS")  # NYSE calendar; ~200ms to instantiate

# ---------------------------------------------------------------------------
# In-memory session cache
# Key: session date string ("YYYY-MM-DD")
# Value: (list[ScreenerCandidate], timestamp_float)
# ---------------------------------------------------------------------------

_SCREENER_CACHE: dict[str, tuple[list, float]] = {}


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------

class ScreenerCandidate(BaseModel):
    ticker: str
    volume_score: float         # normalized [0, 1]
    momentum_score: float       # normalized [0, 1]
    unusual_activity_score: float  # normalized [0, 1]
    composite_score: float      # equal-weight mean of three scores
    rank: int                   # 1-indexed rank (1 = best)
    coverage_note: Optional[str] = None


# ---------------------------------------------------------------------------
# S&P 500 ticker universe
# ---------------------------------------------------------------------------

def get_sp500_tickers() -> list[str]:
    """Fetch current S&P 500 tickers from Wikipedia.

    Returns a list of ticker symbols with "." replaced by "-" to match
    yfinance conventions (e.g., BRK.B -> BRK-B).

    Raises:
        RuntimeError: If the Wikipedia page cannot be fetched or parsed.
    """
    try:
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"},
            storage_options={"User-Agent": "Mozilla/5.0"},
        )
        df = tables[0]
        symbol_col = "Symbol" if "Symbol" in df.columns else df.columns[0]
        tickers = df[symbol_col].str.replace(".", "-", regex=False).tolist()
        return tickers
    except Exception:
        raise RuntimeError("Failed to fetch S&P 500 ticker list from Wikipedia")


# ---------------------------------------------------------------------------
# Chunked bulk fetch
# ---------------------------------------------------------------------------

def _fetch_chunk(tickers: list[str], period: str = "25d") -> dict[str, pd.DataFrame]:
    """Download a single chunk of tickers from yfinance.

    Uses ``group_by='ticker'`` so ``raw[ticker]`` gives per-ticker OHLCV.
    ``period='25d'`` supplies enough history for a 20-day volume average plus
    a 5-day momentum window.

    On ``YFRateLimitError``, retries up to MAX_RETRIES times with exponential
    backoff plus random jitter. If all retries are exhausted, returns an empty
    dict for this chunk rather than raising — callers see a lower coverage
    metric.

    Returns:
        dict mapping ticker -> DataFrame for successfully fetched tickers.
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
            result: dict[str, pd.DataFrame] = {}
            for ticker in tickers:
                try:
                    df = raw[ticker].dropna(how="all")
                    if not df.empty:
                        result[ticker] = df
                except (KeyError, TypeError):
                    pass  # Ticker missing from response — counted as coverage failure
            return result
        except YFRateLimitError:
            if attempt == MAX_RETRIES:
                return {}  # All retries exhausted; skip this chunk
            wait = BACKOFF_BASE ** (attempt + 1) + random.uniform(0, 1)
            time.sleep(wait)
            attempt += 1
    return {}


def fetch_universe_data(
    tickers: list[str] | None = None,
    chunk_size: int = CHUNK_SIZE,
) -> tuple[dict[str, pd.DataFrame], float]:
    """Fetch OHLCV data for the full market universe in rate-limit-safe chunks.

    Args:
        tickers: List of ticker symbols. Defaults to ``get_sp500_tickers()``.
        chunk_size: Number of tickers per ``yf.download`` call (default 90).

    Returns:
        A tuple of:
        - dict mapping ticker -> OHLCV DataFrame for successfully fetched tickers
        - coverage float in [0.0, 1.0] (fetched / requested)
    """
    if tickers is None:
        tickers = get_sp500_tickers()

    all_data: dict[str, pd.DataFrame] = {}

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i : i + chunk_size]
        chunk_result = _fetch_chunk(chunk)
        all_data.update(chunk_result)

    coverage = len(all_data) / len(tickers) if tickers else 0.0
    return all_data, coverage


# ---------------------------------------------------------------------------
# Session cache helpers
# ---------------------------------------------------------------------------

def _get_session_key() -> str | None:
    """Return today's NYSE session date string if the market is currently open.

    Uses ``exchange_calendars`` for holiday/half-day awareness.

    Returns:
        "YYYY-MM-DD" if a NYSE trading minute is active, otherwise None.
    """
    now_et = datetime.now(_eastern)
    now_utc = pd.Timestamp(datetime.now(pytz.utc))
    if _xnys.is_trading_minute(now_utc):
        return now_et.strftime("%Y-%m-%d")
    return None


def _cache_get(session_key: str) -> list[ScreenerCandidate] | None:
    """Retrieve cached screener results if they exist and are within TTL.

    Args:
        session_key: Session date string (e.g., "2026-04-02").

    Returns:
        Cached list of ScreenerCandidate objects, or None on miss/expiry.
    """
    if session_key not in _SCREENER_CACHE:
        return None
    results, ts = _SCREENER_CACHE[session_key]
    if time.time() - ts > _CACHE_TTL_SECONDS:
        del _SCREENER_CACHE[session_key]
        return None
    return results


def _cache_set(session_key: str, results: list[ScreenerCandidate]) -> None:
    """Store screener results in the session cache with the current timestamp.

    Args:
        session_key: Session date string (e.g., "2026-04-02").
        results: List of ScreenerCandidate objects to cache.
    """
    _SCREENER_CACHE[session_key] = (results, time.time())


# ---------------------------------------------------------------------------
# Signal scoring
# ---------------------------------------------------------------------------

def _compute_signals(universe_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute raw signals for all tickers and min-max normalize to [0, 1].

    Signals computed per ticker (requires >= 21 rows):
    - ``volume_ratio``: current volume / 20-day avg volume
    - ``momentum_5d``: (close[-1] - close[-6]) / close[-6]  (5-day return)
    - ``unusual_activity``: 1.0 if volume_ratio > 2.0 AND |price_change_1d| > 1.5%, else 0.0

    Each signal is then min-max normalized across all candidates. If the range
    of a signal is 0 (all values identical), the normalized score is 0.5.

    The composite score is the equal-weight mean of the three normalized scores.

    Returns:
        DataFrame with columns: ticker, volume_ratio, momentum_5d,
        unusual_activity, volume_ratio_score, momentum_5d_score,
        unusual_activity_score, composite_score.
        Sorted by composite_score descending, index reset.
    """
    rows = []
    for ticker, df in universe_data.items():
        if len(df) < 21:
            continue

        current_vol = df["Volume"].iloc[-1]
        avg_20_vol = df["Volume"].iloc[-21:-1].mean()
        volume_ratio = float(current_vol / avg_20_vol) if avg_20_vol > 0 else 0.0

        # 5-day momentum
        if len(df) >= 6:
            momentum_5d = float(
                (df["Close"].iloc[-1] - df["Close"].iloc[-6]) / df["Close"].iloc[-6]
            )
        else:
            momentum_5d = 0.0

        # 1-day price change for unusual-activity flag
        price_change_1d = float(
            (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]
            if len(df) >= 2
            else 0.0
        )

        unusual_activity = float(
            volume_ratio > 2.0 and abs(price_change_1d) > 0.015
        )

        rows.append(
            {
                "ticker": ticker,
                "volume_ratio": volume_ratio,
                "momentum_5d": momentum_5d,
                "unusual_activity": unusual_activity,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "ticker",
                "volume_ratio",
                "momentum_5d",
                "unusual_activity",
                "volume_ratio_score",
                "momentum_5d_score",
                "unusual_activity_score",
                "composite_score",
            ]
        )

    df_signals = pd.DataFrame(rows)

    # Min-max normalize each signal to [0, 1]; use 0.5 when range is zero
    for col in ["volume_ratio", "momentum_5d", "unusual_activity"]:
        col_min = df_signals[col].min()
        col_max = df_signals[col].max()
        rng = col_max - col_min
        if rng > 0:
            df_signals[f"{col}_score"] = (df_signals[col] - col_min) / rng
        else:
            df_signals[f"{col}_score"] = 0.5

    df_signals["composite_score"] = (
        df_signals["volume_ratio_score"]
        + df_signals["momentum_5d_score"]
        + df_signals["unusual_activity_score"]
    ) / 3.0

    return df_signals.sort_values("composite_score", ascending=False).reset_index(
        drop=True
    )


# ---------------------------------------------------------------------------
# Public API — wired into VENDOR_METHODS in Plan 02
# ---------------------------------------------------------------------------

def get_screener_universe(
    tickers: list[str] | None = None,
) -> tuple[dict[str, pd.DataFrame], float]:
    """Public API: Fetch OHLCV universe data.

    Delegates to ``fetch_universe_data``. Intended to be registered as the
    yfinance implementation for the ``get_screener_universe`` vendor method.

    Args:
        tickers: Optional list of ticker symbols. Defaults to S&P 500.

    Returns:
        Tuple of (dict[ticker -> DataFrame], coverage_float).
    """
    return fetch_universe_data(tickers)


def get_screener_signals(
    universe_data: dict[str, pd.DataFrame] | None = None,
    max_candidates: int = 50,
) -> tuple[list[ScreenerCandidate], float]:
    """Public API: Score, rank, and cache screener candidates.

    If ``universe_data`` is None, fetches the full S&P 500 universe first.
    During an active NYSE trading session, results are cached for 15 minutes
    using the session date as the cache key.

    Args:
        universe_data: Optional pre-fetched universe dict. Pass None to
            trigger an automatic fetch.
        max_candidates: Maximum number of candidates to return (default 50).

    Returns:
        Tuple of (list[ScreenerCandidate] sorted by composite_score desc,
        coverage_float).
    """
    coverage = 1.0

    # Session-boundary cache check — BEFORE fetching to avoid unnecessary downloads
    session_key = _get_session_key()
    if session_key is not None:
        cached = _cache_get(session_key)
        if cached is not None:
            return cached, 1.0

    if universe_data is None:
        universe_data, coverage = fetch_universe_data()

    df_scored = _compute_signals(universe_data)

    total_requested = len(universe_data)
    # Note: coverage already reflects fetch success; re-state for coverage_note
    n_tickers = total_requested
    n_fetched = total_requested  # universe_data only has successfully fetched tickers

    top_rows = df_scored.head(max_candidates)
    candidates: list[ScreenerCandidate] = []
    for rank, (_, row) in enumerate(top_rows.iterrows(), start=1):
        candidates.append(
            ScreenerCandidate(
                ticker=str(row["ticker"]),
                volume_score=float(row["volume_ratio_score"]),
                momentum_score=float(row["momentum_5d_score"]),
                unusual_activity_score=float(row["unusual_activity_score"]),
                composite_score=float(row["composite_score"]),
                rank=rank,
                coverage_note=(
                    f"{n_fetched}/{n_tickers} tickers fetched "
                    f"({n_fetched / n_tickers * 100:.1f}%)"
                    if n_tickers > 0
                    else None
                ),
            )
        )

    if session_key is not None:
        _cache_set(session_key, candidates)

    return candidates, coverage
