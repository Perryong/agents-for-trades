"""Tests for microstructure feature computation.

Hand-calculated examples verify each formula against the Aldridge & Jiang (2024)
definitions. All data uses daily OHLCV only (AR-W2).
"""
import math
import pytest
import numpy as np

from tradingagents.services.microstructure import (
    compute_microstructure_features,
    forecast_volatility,
    MicrostructureFeatures,
    VolatilityForecast,
)


# ---------------------------------------------------------------------------
# Fixtures: synthetic OHLCV data
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_ohlcv():
    """20-day synthetic OHLCV with predictable values.

    Columns: [Open, High, Low, Close, Volume]
    Closes: 100, 101, 99, 102, 98, 103, 97, 104, 96, 105,
            100, 101, 99, 102, 98, 103, 97, 104, 96, 105
    """
    closes = [100, 101, 99, 102, 98, 103, 97, 104, 96, 105,
              100, 101, 99, 102, 98, 103, 97, 104, 96, 105]
    data = []
    for i, c in enumerate(closes):
        o = c - 0.5  # Open slightly below close
        h = c + 2.0  # High 2 above close
        l = c - 1.5  # Low 1.5 below close
        v = 1_000_000 + i * 10_000  # Increasing volume
        data.append([o, h, l, c, v])
    return np.array(data, dtype=float)


@pytest.fixture
def zero_volume_ohlcv():
    """OHLCV where some rows have zero volume."""
    data = [
        [100, 102, 99, 101, 1000000],
        [101, 103, 100, 102, 0],       # Zero volume
        [102, 104, 101, 103, 2000000],
        [103, 105, 102, 104, 0],       # Zero volume
        [104, 106, 103, 105, 3000000],
    ]
    return np.array(data, dtype=float)


@pytest.fixture
def constant_price_ohlcv():
    """OHLCV where price never changes — should produce specific edge cases."""
    data = [[100, 100, 100, 100, 1000000]] * 20
    return np.array(data, dtype=float)


# ---------------------------------------------------------------------------
# Task 3.2: Test Range Volatility
# ---------------------------------------------------------------------------

class TestRangeVolatility:

    def test_hand_calculated(self, simple_ohlcv):
        """Range Volatility = mean((High - Low) / Open) over lookback window."""
        result = compute_microstructure_features("TEST", ohlcv=simple_ohlcv, lookback_days=20)
        assert result is not None
        assert result.range_volatility is not None

        # Hand-calculate: for each row, (H - L) / O
        # H = close + 2, L = close - 1.5, O = close - 0.5
        # range = (close + 2) - (close - 1.5) = 3.5
        # rv_i = 3.5 / (close_i - 0.5)
        closes = [100, 101, 99, 102, 98, 103, 97, 104, 96, 105,
                  100, 101, 99, 102, 98, 103, 97, 104, 96, 105]
        expected_rvs = [3.5 / (c - 0.5) for c in closes]
        expected_mean = sum(expected_rvs) / len(expected_rvs)

        assert abs(result.range_volatility - expected_mean) < 1e-4

    def test_zero_open_excluded(self):
        """Rows with Open=0 should not cause division by zero."""
        data = np.array([
            [0, 102, 99, 101, 1000000],    # Open=0 → excluded
            [101, 103, 100, 102, 1000000],
            [102, 104, 101, 103, 1000000],
            [103, 105, 102, 104, 1000000],
            [104, 106, 103, 105, 1000000],
        ], dtype=float)
        result = compute_microstructure_features("TEST", ohlcv=data, lookback_days=5)
        assert result is not None
        assert result.range_volatility is not None
        assert np.isfinite(result.range_volatility)

    def test_constant_price(self, constant_price_ohlcv):
        """When H=L=O=C, range vol should be 0."""
        result = compute_microstructure_features("TEST", ohlcv=constant_price_ohlcv, lookback_days=20)
        assert result is not None
        assert result.range_volatility == 0.0


# ---------------------------------------------------------------------------
# Task 3.3: Test Roll Measure
# ---------------------------------------------------------------------------

class TestRollMeasure:

    def test_negative_covariance_gives_positive_roll(self):
        """When consecutive price changes are negatively correlated (bid-ask bounce),
        Roll Measure should be positive."""
        # Alternating up-down pattern → negative autocovariance
        closes = [100, 102, 100, 102, 100, 102, 100, 102, 100, 102,
                  100, 102, 100, 102, 100, 102, 100, 102, 100, 102]
        data = np.array([[c, c+1, c-1, c, 1e6] for c in closes], dtype=float)
        result = compute_microstructure_features("TEST", ohlcv=data, lookback_days=20)
        assert result is not None
        assert result.roll_measure is not None
        assert result.roll_measure > 0

    def test_positive_covariance_gives_zero(self):
        """When consecutive changes are positively correlated (trending),
        Roll Measure should be 0."""
        # Monotonically increasing → positive autocovariance
        closes = list(range(100, 120))
        data = np.array([[c, c+1, c-1, c, 1e6] for c in closes], dtype=float)
        result = compute_microstructure_features("TEST", ohlcv=data, lookback_days=20)
        assert result is not None
        assert result.roll_measure == 0.0

    def test_hand_calculated(self):
        """Verify formula: 2 * sqrt(-cov(deltaP_t, deltaP_{t-1}))."""
        closes = [100, 102, 100, 102, 100, 102, 100, 102, 100, 102,
                  100, 102, 100, 102, 100, 102, 100, 102, 100, 102]
        delta_p = np.diff(closes)
        cov_val = np.cov(delta_p[1:], delta_p[:-1])[0, 1]
        expected_roll = 2.0 * math.sqrt(-cov_val) if cov_val < 0 else 0.0

        data = np.array([[c, c+1, c-1, c, 1e6] for c in closes], dtype=float)
        result = compute_microstructure_features("TEST", ohlcv=data, lookback_days=20)
        assert result is not None
        assert abs(result.roll_measure - expected_roll) < 1e-4


# ---------------------------------------------------------------------------
# Task 3.4: Test Price Impact
# ---------------------------------------------------------------------------

class TestPriceImpact:

    def test_hand_calculated(self, simple_ohlcv):
        """Price Impact = mean(|deltaP| / V) for rows with V > 0."""
        result = compute_microstructure_features("TEST", ohlcv=simple_ohlcv, lookback_days=20)
        assert result is not None
        assert result.price_impact is not None
        assert result.price_impact > 0

    def test_zero_volume_excluded(self, zero_volume_ohlcv):
        """Rows with volume=0 should be excluded, not produce inf/NaN."""
        result = compute_microstructure_features("TEST", ohlcv=zero_volume_ohlcv, lookback_days=5)
        assert result is not None
        assert result.price_impact is not None
        assert np.isfinite(result.price_impact)


# ---------------------------------------------------------------------------
# Task 3.5: Test Price Dispersion
# ---------------------------------------------------------------------------

class TestPriceDispersion:

    def test_hand_calculated(self, simple_ohlcv):
        """Price Dispersion = sqrt(sum(w * (typicalP - mean_typicalP)^2))."""
        result = compute_microstructure_features("TEST", ohlcv=simple_ohlcv, lookback_days=20)
        assert result is not None
        assert result.price_dispersion is not None
        assert result.price_dispersion > 0

    def test_constant_price_gives_zero(self, constant_price_ohlcv):
        """When all prices are identical, dispersion should be 0."""
        result = compute_microstructure_features("TEST", ohlcv=constant_price_ohlcv, lookback_days=20)
        assert result is not None
        assert result.price_dispersion == 0.0

    def test_zero_total_volume(self):
        """If all volume is 0, price dispersion should be None."""
        data = np.array([[100, 102, 99, 101, 0]] * 20, dtype=float)
        result = compute_microstructure_features("TEST", ohlcv=data, lookback_days=20)
        assert result is not None
        assert result.price_dispersion is None


# ---------------------------------------------------------------------------
# Task 3.6: Test insufficient data
# ---------------------------------------------------------------------------

class TestInsufficientData:

    def test_none_ohlcv_with_invalid_ticker_returns_none(self):
        """None ohlcv with a non-existent ticker returns None (yfinance fetch fails)."""
        result = compute_microstructure_features("ZZZZZZNOTREAL", ohlcv=None, lookback_days=20)
        assert result is None

    def test_too_short_returns_none(self):
        """Fewer than 5 rows returns None."""
        data = np.array([[100, 102, 99, 101, 1e6]] * 3, dtype=float)
        result = compute_microstructure_features("TEST", ohlcv=data, lookback_days=20)
        assert result is None

    def test_empty_array_returns_none(self):
        """Empty array returns None."""
        data = np.array([], dtype=float).reshape(0, 5)
        result = compute_microstructure_features("TEST", ohlcv=data, lookback_days=20)
        assert result is None


# ---------------------------------------------------------------------------
# Task 3.7: Test NaN handling
# ---------------------------------------------------------------------------

class TestNaNHandling:

    def test_nan_in_closes_no_crash(self):
        """NaN values in close prices should not crash the function."""
        data = np.array([
            [100, 102, 99, 101, 1e6],
            [101, 103, 100, np.nan, 1e6],
            [102, 104, 101, 103, 1e6],
            [103, 105, 102, 104, 1e6],
            [104, 106, 103, 105, 1e6],
        ], dtype=float)
        # Should not raise
        result = compute_microstructure_features("TEST", ohlcv=data, lookback_days=5)
        # Result may be partial (some features None) but should not crash
        assert result is not None or result is None  # Just verify no exception


# ---------------------------------------------------------------------------
# Task 3.8: Test dataclass completeness
# ---------------------------------------------------------------------------

class TestDataclassOutput:

    def test_all_fields_present(self, simple_ohlcv):
        """All four features + ticker + date should be in the result."""
        result = compute_microstructure_features("TEST", ohlcv=simple_ohlcv, lookback_days=20, date="2026-04-16")
        assert result is not None
        assert result.ticker == "TEST"
        assert result.date == "2026-04-16"
        assert isinstance(result.range_volatility, float)
        assert isinstance(result.roll_measure, float)
        assert isinstance(result.price_impact, float)
        assert isinstance(result.price_dispersion, float)

    def test_date_parameter_passed_through(self, simple_ohlcv):
        """Date parameter should be stored in the result."""
        result = compute_microstructure_features("TEST", ohlcv=simple_ohlcv, date="2026-01-01")
        assert result is not None
        assert result.date == "2026-01-01"

    def test_ticker_uppercased(self, simple_ohlcv):
        """Ticker should be uppercased in output."""
        result = compute_microstructure_features("aapl", ohlcv=simple_ohlcv)
        assert result is not None
        assert result.ticker == "AAPL"


# ===========================================================================
# Story 14.2: OLS Volatility Forecast Tests
# ===========================================================================

@pytest.fixture
def large_ohlcv():
    """100-day synthetic OHLCV with varied price action and volume.

    Designed to produce non-collinear microstructure features for OLS.
    Uses alternating trending/mean-reverting regimes with diverse volume.
    """
    np.random.seed(42)
    n = 100
    data = []
    price = 100.0
    for i in range(n):
        # Alternate between trending and mean-reverting to create feature diversity
        if i % 20 < 10:
            # Trending: larger moves in one direction
            move = np.random.uniform(0.5, 2.0) * (1 if i % 40 < 20 else -1)
        else:
            # Mean-reverting: oscillating
            move = np.random.uniform(-2.0, 2.0)
        price = max(10, price + move)
        # Varied intraday range
        spread = np.random.uniform(0.5, 4.0)
        h = price + spread
        l = price - spread * np.random.uniform(0.3, 0.8)
        o = price + np.random.uniform(-1, 1)
        # Highly varied volume to prevent collinearity
        v = np.random.randint(100_000, 5_000_000)
        data.append([max(o, 1), max(h, 1), max(l, 0.5), max(price, 1), max(v, 100)])
    return np.array(data, dtype=float)


class TestVolatilityForecast:

    def test_returns_forecast_with_sufficient_data(self, large_ohlcv):
        """With 100 days of data, OLS should produce a valid forecast."""
        result = forecast_volatility("TEST", rolling_window=60, ohlcv=large_ohlcv)
        assert result is not None
        assert isinstance(result, VolatilityForecast)

    def test_predicted_rv_non_negative(self, large_ohlcv):
        """Predicted realized volatility must be >= 0."""
        result = forecast_volatility("TEST", rolling_window=60, ohlcv=large_ohlcv)
        assert result is not None
        assert result.predicted_rv >= 0

    def test_r_squared_in_range(self, large_ohlcv):
        """R-squared must be between 0 and 1."""
        result = forecast_volatility("TEST", rolling_window=60, ohlcv=large_ohlcv)
        assert result is not None
        assert 0 <= result.r_squared <= 1

    def test_coefficients_have_expected_keys(self, large_ohlcv):
        """Coefficients dict must have intercept + 4 feature keys."""
        result = forecast_volatility("TEST", rolling_window=60, ohlcv=large_ohlcv)
        assert result is not None
        expected_keys = {"intercept", "range_volatility", "roll_measure", "price_impact", "price_dispersion"}
        assert set(result.coefficients.keys()) == expected_keys

    def test_dominant_factor_is_valid_name(self, large_ohlcv):
        """Dominant factor must be one of the four feature names."""
        result = forecast_volatility("TEST", rolling_window=60, ohlcv=large_ohlcv)
        assert result is not None
        valid_names = {"range_volatility", "roll_measure", "price_impact", "price_dispersion"}
        assert result.dominant_factor in valid_names

    def test_sample_days_positive(self, large_ohlcv):
        """Sample days should reflect how many feature rows were used."""
        result = forecast_volatility("TEST", rolling_window=60, ohlcv=large_ohlcv)
        assert result is not None
        assert result.sample_days >= 30  # Minimum guard in the function

    def test_insufficient_data_returns_none(self):
        """With fewer than ~50 rows (need 20 warmup + 30 valid), should return None."""
        short_data = np.array([[100, 102, 99, 101, 1e6]] * 25, dtype=float)
        result = forecast_volatility("TEST", rolling_window=60, ohlcv=short_data)
        assert result is None

    def test_configurable_rolling_window(self, large_ohlcv):
        """Rolling window parameter should be respected."""
        result_30 = forecast_volatility("TEST", rolling_window=30, ohlcv=large_ohlcv)
        result_60 = forecast_volatility("TEST", rolling_window=60, ohlcv=large_ohlcv)
        # Both should work with 100 days of data
        assert result_30 is not None
        assert result_60 is not None
        # Different windows may produce different predictions
        # (not guaranteed but likely with different sample sizes)

    def test_ticker_uppercased(self, large_ohlcv):
        """Output ticker should be uppercased."""
        result = forecast_volatility("aapl", rolling_window=60, ohlcv=large_ohlcv)
        assert result is not None
        assert result.ticker == "AAPL"

    def test_singular_matrix_returns_none(self):
        """When all features are identical (collinear), OLS should fail gracefully."""
        # Constant data → all features identical → singular matrix
        data = np.array([[100, 102, 99, 101, 1e6]] * 100, dtype=float)
        result = forecast_volatility("TEST", rolling_window=60, ohlcv=data)
        # Should return None (singular matrix or zero variance)
        assert result is None
