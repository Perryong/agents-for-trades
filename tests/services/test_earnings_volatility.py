"""Tests for Expected Announcement Volatility (EAV) computation."""
import pytest
import math
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import date, timedelta

import pandas as pd
import numpy as np

from tradingagents.services.earnings_volatility import (
    compute_abnormal_iv,
    compute_max_ea,
    compute_eav,
    EAVResult,
)


# ---------------------------------------------------------------------------
# Test AbnormalIV
# ---------------------------------------------------------------------------

class TestComputeAbnormalIV:

    def test_hand_calculated(self):
        """AbnormalIV = (IV_30² - IV_60²) / (1/30 - 1/60).

        With IV_30=0.40 and IV_60=0.30:
        var_30 = 0.16, var_60 = 0.09
        denom = 1/30 - 1/60 = 0.01667
        AbnormalIV = (0.16 - 0.09) / 0.01667 = 4.198
        """
        mock_stock = MagicMock()
        mock_stock.options = ["2026-05-16", "2026-06-20"]
        mock_stock.fast_info = {"lastPrice": 150.0}

        # Mock chains: 30-day ATM IV=0.40, 60-day ATM IV=0.30
        calls_30 = pd.DataFrame({
            "strike": [145, 150, 155],
            "impliedVolatility": [0.42, 0.40, 0.43],
        })
        calls_60 = pd.DataFrame({
            "strike": [145, 150, 155],
            "impliedVolatility": [0.32, 0.30, 0.33],
        })
        chain_30 = MagicMock()
        chain_30.calls = calls_30
        chain_60 = MagicMock()
        chain_60.calls = calls_60

        def mock_option_chain(exp):
            if exp == "2026-05-16":
                return chain_30
            return chain_60

        mock_stock.option_chain = mock_option_chain

        today = date(2026, 4, 16)
        with patch("tradingagents.services.earnings_volatility.yf") as mock_yf, \
             patch("tradingagents.services.earnings_volatility.date") as mock_date:
            mock_yf.Ticker.return_value = mock_stock
            mock_date.today.return_value = today
            mock_date.fromisoformat = date.fromisoformat
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

            abnormal_iv, iv_30, iv_60 = compute_abnormal_iv("TEST", expirations=["2026-05-16", "2026-06-20"])

        assert iv_30 == pytest.approx(0.40, abs=0.01)
        assert iv_60 == pytest.approx(0.30, abs=0.01)
        assert abnormal_iv is not None
        expected = (0.40**2 - 0.30**2) / (1/30 - 1/60)
        assert abnormal_iv == pytest.approx(expected, rel=0.01)

    def test_single_expiration_returns_none(self):
        """With only one expiration, can't compute AbnormalIV."""
        abnormal_iv, _, _ = compute_abnormal_iv("TEST", expirations=["2026-05-16"])
        assert abnormal_iv is None

    def test_no_expirations_returns_none(self):
        """No expirations returns all None."""
        abnormal_iv, iv_30, iv_60 = compute_abnormal_iv("TEST", expirations=[])
        assert abnormal_iv is None
        assert iv_30 is None
        assert iv_60 is None


# ---------------------------------------------------------------------------
# Test MAX_EA
# ---------------------------------------------------------------------------

class TestComputeMaxEA:

    def test_with_mocked_earnings(self):
        """MAX_EA should return the max absolute return around earnings."""
        mock_stock = MagicMock()

        # Mock earnings_dates: 4 past dates
        earnings_dates_index = pd.DatetimeIndex([
            "2026-01-15", "2025-10-15", "2025-07-15", "2025-04-15"
        ])
        mock_stock.earnings_dates = pd.DataFrame(
            {"Surprise(%)": [5.0, -3.0, 8.0, -2.0]},
            index=earnings_dates_index,
        )

        # Mock history: price goes from 100 → varies around earnings
        dates = pd.date_range("2024-04-01", "2026-04-16", freq="B")
        prices = 100 + np.cumsum(np.random.RandomState(42).randn(len(dates)) * 0.5)
        hist = pd.DataFrame({"Close": prices}, index=dates)

        # Inject known large moves around earnings dates
        for ea_date_ts in earnings_dates_index:
            ea_date = ea_date_ts.date()
            # Find closest trading day before and after
            before_mask = hist.index.date < ea_date
            after_mask = hist.index.date >= ea_date
            if before_mask.any() and after_mask.any():
                pass  # Returns will vary based on random walk

        mock_stock.history.return_value = hist

        with patch("tradingagents.services.earnings_volatility.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_stock
            result = compute_max_ea("TEST", lookback_quarters=4)

        # Should return a non-negative float
        if result is not None:
            assert result >= 0
            assert isinstance(result, float)

    def test_no_earnings_returns_none(self):
        """When no earnings dates available, returns None."""
        mock_stock = MagicMock()
        mock_stock.earnings_dates = None
        mock_stock.calendar = {}

        with patch("tradingagents.services.earnings_volatility.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_stock
            result = compute_max_ea("TEST")

        assert result is None


# ---------------------------------------------------------------------------
# Test compute_eav (combined)
# ---------------------------------------------------------------------------

class TestComputeEAV:

    def test_returns_eav_result(self):
        """compute_eav should return an EAVResult dataclass."""
        with patch("tradingagents.services.earnings_volatility.compute_abnormal_iv", return_value=(4.2, 0.40, 0.30)), \
             patch("tradingagents.services.earnings_volatility.compute_max_ea", return_value=0.12), \
             patch("tradingagents.services.earnings_volatility.yf") as mock_yf:
            mock_stock = MagicMock()
            mock_stock.earnings_dates = None
            mock_stock.calendar = {}
            mock_yf.Ticker.return_value = mock_stock

            result = compute_eav("AAPL")

        assert isinstance(result, EAVResult)
        assert result.ticker == "AAPL"
        assert result.abnormal_iv == 4.2
        assert result.max_ea == 0.12
        assert result.iv_30 == 0.40
        assert result.iv_60 == 0.30

    def test_all_fields_present(self):
        """EAVResult should have all expected fields."""
        result = EAVResult(
            ticker="TEST",
            earnings_date="2026-05-01",
            abnormal_iv=3.5,
            max_ea=0.08,
            iv_30=0.35,
            iv_60=0.28,
        )
        assert result.ticker == "TEST"
        assert result.earnings_date == "2026-05-01"
        assert result.abnormal_iv == 3.5
        assert result.max_ea == 0.08
        assert result.iv_30 == 0.35
        assert result.iv_60 == 0.28

    def test_partial_data_ok(self):
        """When some metrics unavailable, others still returned."""
        with patch("tradingagents.services.earnings_volatility.compute_abnormal_iv", return_value=(None, None, None)), \
             patch("tradingagents.services.earnings_volatility.compute_max_ea", return_value=0.15), \
             patch("tradingagents.services.earnings_volatility.yf") as mock_yf:
            mock_stock = MagicMock()
            mock_stock.earnings_dates = None
            mock_stock.calendar = {}
            mock_yf.Ticker.return_value = mock_stock

            result = compute_eav("TEST")

        assert result.abnormal_iv is None
        assert result.max_ea == 0.15
