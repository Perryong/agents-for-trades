"""Unit tests for tradingagents.dataflows.screener_data.

Covers SCREEN-01 (bulk fetch + rate-limit retry), SCREEN-02 (signal scoring +
unusual activity threshold + composite score formula), and SCREEN-04 (session
cache TTL and cross-session isolation).

SCREEN-03 (VENDOR_METHODS / TOOLS_CATEGORIES wiring) tests are stubbed and
skipped until Plan 02 wires screener_data into interface.py.

All yfinance and network calls are mocked — no internet access required.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from tradingagents.dataflows.screener_data import (
    ScreenerCandidate,
    fetch_universe_data,
    get_screener_signals,
    _compute_signals,
    _cache_get,
    _cache_set,
    _SCREENER_CACHE,
    _CACHE_TTL_SECONDS,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_ohlcv(
    n_days: int = 25,
    base_close: float = 100.0,
    base_volume: int = 1_000_000,
    last_volume_mult: float = 1.0,
    last_close_change: float = 0.0,
) -> pd.DataFrame:
    """Create a synthetic OHLCV DataFrame with n_days rows."""
    dates = pd.date_range(end="2026-04-01", periods=n_days, freq="B")
    close = [base_close] * (n_days - 1) + [base_close * (1 + last_close_change)]
    volume = [base_volume] * (n_days - 1) + [int(base_volume * last_volume_mult)]
    return pd.DataFrame(
        {
            "Open": close,
            "High": close,
            "Low": close,
            "Close": close,
            "Volume": volume,
        },
        index=dates,
    )


def _make_multi_index_download(tickers: list[str]) -> pd.DataFrame:
    """Create a minimal MultiIndex DataFrame that yf.download returns with group_by='ticker'."""
    frames = {}
    for ticker in tickers:
        df = _make_ohlcv(n_days=25)
        frames[ticker] = df

    # Build MultiIndex columns: (ticker, column)
    iterables = [tickers, ["Open", "High", "Low", "Close", "Volume"]]
    multi_index = pd.MultiIndex.from_product(iterables)
    dates = pd.date_range(end="2026-04-01", periods=25, freq="B")
    data = {}
    for ticker in tickers:
        base_df = _make_ohlcv(n_days=25)
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            data[(ticker, col)] = base_df[col].values
    result = pd.DataFrame(data, index=dates)
    result.columns = pd.MultiIndex.from_tuples(result.columns)
    return result


# ---------------------------------------------------------------------------
# SCREEN-01: Bulk fetch and rate-limit retry
# ---------------------------------------------------------------------------

class TestFetchUniverseReturnsCoverage:
    """test_fetch_universe_returns_coverage: SCREEN-01"""

    def test_fetch_universe_returns_coverage(self):
        """Mocked yf.download with 3 tickers returns dict + coverage=1.0."""
        tickers = ["AAPL", "MSFT", "GOOG"]
        raw = _make_multi_index_download(tickers)

        with patch("tradingagents.dataflows.screener_data.yf.download", return_value=raw):
            result_dict, coverage = fetch_universe_data(tickers)

        assert isinstance(result_dict, dict)
        assert isinstance(coverage, float)
        assert len(result_dict) == 3
        assert coverage == pytest.approx(1.0)


class TestRateLimitRetries:
    """test_rate_limit_retries: SCREEN-01"""

    def test_rate_limit_retries(self):
        """YFRateLimitError raised twice then success; verify 3 yf.download calls total."""
        from yfinance.exceptions import YFRateLimitError

        tickers = ["AAPL"]
        raw = _make_multi_index_download(tickers)

        mock_download = MagicMock(
            side_effect=[
                YFRateLimitError(),
                YFRateLimitError(),
                raw,
            ]
        )

        with patch("tradingagents.dataflows.screener_data.yf.download", mock_download), \
             patch("tradingagents.dataflows.screener_data.time.sleep"):
            result_dict, coverage = fetch_universe_data(["AAPL"], chunk_size=90)

        assert mock_download.call_count == 3


# ---------------------------------------------------------------------------
# SCREEN-02: Signal scoring, composite score, unusual activity
# ---------------------------------------------------------------------------

class TestScoringReturnsSortedCandidates:
    """test_scoring_returns_sorted_candidates: SCREEN-02"""

    def test_scoring_returns_sorted_candidates(self):
        """_compute_signals returns DataFrame sorted by composite_score descending."""
        universe_data = {
            "HIGH": _make_ohlcv(n_days=25, base_volume=1_000_000, last_volume_mult=5.0, last_close_change=0.05),
            "MID": _make_ohlcv(n_days=25, base_volume=1_000_000, last_volume_mult=2.0, last_close_change=0.01),
            "LOW": _make_ohlcv(n_days=25, base_volume=1_000_000, last_volume_mult=0.5, last_close_change=-0.01),
        }

        result = _compute_signals(universe_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        # composite_score must be monotonically non-increasing
        scores = result["composite_score"].tolist()
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Row {i} score {scores[i]} < row {i+1} score {scores[i+1]}: not sorted desc"
            )


class TestCompositeScoreIsEqualWeightMean:
    """test_composite_score_is_equal_weight_mean: SCREEN-02"""

    def test_composite_score_is_equal_weight_mean(self):
        """composite_score == (volume_ratio_score + momentum_5d_score + unusual_activity_score) / 3."""
        universe_data = {
            "A": _make_ohlcv(n_days=25, base_volume=1_000_000, last_volume_mult=3.0, last_close_change=0.03),
            "B": _make_ohlcv(n_days=25, base_volume=1_000_000, last_volume_mult=1.5, last_close_change=0.01),
            "C": _make_ohlcv(n_days=25, base_volume=1_000_000, last_volume_mult=0.8, last_close_change=-0.02),
        }

        result = _compute_signals(universe_data)

        for _, row in result.iterrows():
            expected = (
                row["volume_ratio_score"]
                + row["momentum_5d_score"]
                + row["unusual_activity_score"]
            ) / 3.0
            assert row["composite_score"] == pytest.approx(expected, abs=1e-9)


class TestUnusualActivityThreshold:
    """test_unusual_activity_threshold: SCREEN-02"""

    def test_unusual_activity_threshold(self):
        """Unusual activity flags correctly based on volume_ratio > 2.0 AND |price_change| > 1.5%.

        Ticker A: volume = 2.5x avg, price change = +2% -> raw unusual_activity = 1.0
        Ticker B: volume = 1.5x avg, price change = +2% -> raw unusual_activity = 0.0 (fails volume)
        Ticker C: volume = 2.5x avg, price change = +0.5% -> raw unusual_activity = 0.0 (fails price)
        """
        universe_data = {
            "A": _make_ohlcv(n_days=25, base_volume=1_000_000, last_volume_mult=2.5, last_close_change=0.02),
            "B": _make_ohlcv(n_days=25, base_volume=1_000_000, last_volume_mult=1.5, last_close_change=0.02),
            "C": _make_ohlcv(n_days=25, base_volume=1_000_000, last_volume_mult=2.5, last_close_change=0.005),
        }

        result = _compute_signals(universe_data)

        a_row = result[result["ticker"] == "A"].iloc[0]
        b_row = result[result["ticker"] == "B"].iloc[0]
        c_row = result[result["ticker"] == "C"].iloc[0]

        assert a_row["unusual_activity"] == pytest.approx(1.0), "Ticker A should have unusual_activity=1.0"
        assert b_row["unusual_activity"] == pytest.approx(0.0), "Ticker B should have unusual_activity=0.0 (volume too low)"
        assert c_row["unusual_activity"] == pytest.approx(0.0), "Ticker C should have unusual_activity=0.0 (price change too small)"


# ---------------------------------------------------------------------------
# SCREEN-03: VENDOR_METHODS / TOOLS_CATEGORIES integration — deferred to Plan 02
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="VENDOR_METHODS wiring done in Plan 02")
def test_vendor_methods_has_screener_keys():
    """VENDOR_METHODS has get_screener_universe and get_screener_signals keys."""
    from tradingagents.dataflows.interface import VENDOR_METHODS
    assert "get_screener_universe" in VENDOR_METHODS
    assert "yfinance" in VENDOR_METHODS["get_screener_universe"]
    assert "get_screener_signals" in VENDOR_METHODS
    assert "yfinance" in VENDOR_METHODS["get_screener_signals"]


@pytest.mark.skip(reason="VENDOR_METHODS wiring done in Plan 02")
def test_tools_categories_has_screener_data():
    """TOOLS_CATEGORIES has screener_data category with get_screener_universe and get_screener_signals."""
    from tradingagents.dataflows.interface import TOOLS_CATEGORIES
    assert "screener_data" in TOOLS_CATEGORIES
    tools = TOOLS_CATEGORIES["screener_data"]["tools"]
    assert "get_screener_universe" in tools
    assert "get_screener_signals" in tools


@pytest.mark.skip(reason="VENDOR_METHODS wiring done in Plan 02")
def test_route_to_vendor_screener_universe():
    """route_to_vendor('get_screener_universe') calls the yfinance implementation."""
    from tradingagents.dataflows.interface import route_to_vendor, VENDOR_METHODS

    mock_result = ({"AAPL": _make_ohlcv()}, 1.0)
    with patch.dict(
        "tradingagents.dataflows.interface.VENDOR_METHODS",
        {
            "get_screener_universe": {
                "yfinance": MagicMock(return_value=mock_result),
            }
        },
    ):
        with patch(
            "tradingagents.dataflows.interface.get_vendor",
            return_value="yfinance",
        ):
            result = route_to_vendor("get_screener_universe")
    assert result == mock_result


# ---------------------------------------------------------------------------
# SCREEN-04: Session cache TTL and cross-session isolation
# ---------------------------------------------------------------------------

class TestCacheHitWithinTTL:
    """test_cache_hit_within_ttl: SCREEN-04"""

    def setup_method(self):
        _SCREENER_CACHE.clear()

    def test_cache_hit_within_ttl(self):
        """Second call to get_screener_signals does not invoke yf.download (cache hit)."""
        tickers = ["AAPL", "MSFT", "GOOG"]
        raw = _make_multi_index_download(tickers)

        mock_download = MagicMock(return_value=raw)

        with patch("tradingagents.dataflows.screener_data.yf.download", mock_download), \
             patch("tradingagents.dataflows.screener_data.get_sp500_tickers", return_value=tickers), \
             patch("tradingagents.dataflows.screener_data._get_session_key", return_value="2026-04-01"):
            _call1, _ = get_screener_signals()
            _call2, _ = get_screener_signals()

        # yf.download called only once; second call served from cache
        assert mock_download.call_count == 1


class TestCacheMissAfterTTL:
    """test_cache_miss_after_ttl: SCREEN-04"""

    def setup_method(self):
        _SCREENER_CACHE.clear()

    def test_cache_miss_after_ttl(self):
        """After TTL expires (>15 min), second call to get_screener_signals triggers fresh fetch."""
        tickers = ["AAPL", "MSFT", "GOOG"]
        raw = _make_multi_index_download(tickers)

        mock_download = MagicMock(return_value=raw)

        # Simulate: first call at T=0, cache check on second call sees T=960 (16 min later)
        # time.time() is called in: _cache_set (to store ts), and _cache_get (to check age)
        # We need: first set stores ts=0, second get checks time.time()-ts > TTL
        time_sequence = [
            0,    # _cache_set stores ts=0 on first call
            960,  # _cache_get: time.time() - 0 = 960 > 900 (15 min) -> miss
            960,  # _cache_set stores ts=960 on second call
        ]
        mock_time = MagicMock(side_effect=time_sequence)

        with patch("tradingagents.dataflows.screener_data.yf.download", mock_download), \
             patch("tradingagents.dataflows.screener_data.get_sp500_tickers", return_value=tickers), \
             patch("tradingagents.dataflows.screener_data._get_session_key", return_value="2026-04-01"), \
             patch("tradingagents.dataflows.screener_data.time.time", mock_time):
            get_screener_signals()
            get_screener_signals()

        # yf.download called twice (cache expired after TTL)
        assert mock_download.call_count == 2


class TestCacheIsolatesBySessionDate:
    """test_cache_isolates_by_session_date: SCREEN-04"""

    def setup_method(self):
        _SCREENER_CACHE.clear()

    def test_cache_isolates_by_session_date(self):
        """Different session date keys cause cache misses (cross-session isolation)."""
        tickers = ["AAPL", "MSFT", "GOOG"]
        raw = _make_multi_index_download(tickers)

        mock_download = MagicMock(return_value=raw)

        session_keys = iter(["2026-04-01", "2026-04-02"])

        with patch("tradingagents.dataflows.screener_data.yf.download", mock_download), \
             patch("tradingagents.dataflows.screener_data.get_sp500_tickers", return_value=tickers), \
             patch("tradingagents.dataflows.screener_data._get_session_key", side_effect=session_keys):
            get_screener_signals()
            get_screener_signals()

        # yf.download called twice (different session keys -> no cache hit)
        assert mock_download.call_count == 2
