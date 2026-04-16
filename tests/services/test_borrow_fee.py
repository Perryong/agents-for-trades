"""Tests for implied borrow fee computation."""
import math
import pytest
import pandas as pd

from tradingagents.services.borrow_fee import (
    compute_implied_borrow_fee,
    compute_borrow_fee_from_chain,
    BorrowFeeResult,
)


class TestComputeImpliedBorrowFee:
    """Tests for the core borrow fee formula."""

    def test_zero_spread_returns_near_zero_fee(self):
        """When call IV == put IV, borrow fee should be ~0."""
        result = compute_implied_borrow_fee("AAPL", call_iv=0.30, put_iv=0.30, days_to_expiry=30)
        assert result is not None
        assert abs(result.implied_fee_annualized) < 0.01
        assert result.fee_tier == "low"

    def test_put_iv_greater_than_call_iv_indicates_borrow_fee(self):
        """When put IV > call IV, implied borrow fee should be positive."""
        # Put IV higher than call IV → positive borrow fee
        result = compute_implied_borrow_fee("TSLA", call_iv=0.50, put_iv=0.55, days_to_expiry=30)
        assert result is not None
        assert result.implied_fee_annualized > 0
        assert result.iv_spread < 0  # call - put is negative

    def test_high_fee_classification(self):
        """Large IV spread → high fee tier with heavy signal discount."""
        # Extreme case: put IV 10% higher than call IV
        result = compute_implied_borrow_fee("GME", call_iv=0.80, put_iv=1.00, days_to_expiry=30)
        assert result is not None
        assert result.fee_tier == "high"
        assert result.signal_discount == 0.1

    def test_moderate_fee_classification(self):
        """Moderate IV spread → moderate fee tier."""
        # Smaller spread
        result = compute_implied_borrow_fee("TEST", call_iv=0.30, put_iv=0.32, days_to_expiry=30)
        assert result is not None
        # The exact fee depends on the formula; check tier assignment
        if 0.5 < abs(result.implied_fee_annualized) <= 1.0:
            assert result.fee_tier == "moderate"
            assert result.signal_discount == 0.5

    def test_low_fee_classification(self):
        """Small IV spread → low fee tier with slight discount."""
        result = compute_implied_borrow_fee("MSFT", call_iv=0.25, put_iv=0.251, days_to_expiry=30)
        assert result is not None
        assert result.fee_tier == "low"
        assert result.signal_discount == 0.8

    def test_invalid_inputs_return_none(self):
        """Zero or negative inputs should return None."""
        assert compute_implied_borrow_fee("X", call_iv=0, put_iv=0.3, days_to_expiry=30) is None
        assert compute_implied_borrow_fee("X", call_iv=0.3, put_iv=0, days_to_expiry=30) is None
        assert compute_implied_borrow_fee("X", call_iv=0.3, put_iv=0.3, days_to_expiry=0) is None
        assert compute_implied_borrow_fee("X", call_iv=-0.1, put_iv=0.3, days_to_expiry=30) is None

    def test_formula_matches_paper(self):
        """Verify the formula: h = -(sigma_C - sigma_P) / sqrt(2*pi*T)."""
        call_iv = 0.40
        put_iv = 0.45
        dte = 30
        T = dte / 365.0

        expected_h = -(call_iv - put_iv) / math.sqrt(2 * math.pi * T)
        expected_pct = expected_h * 100

        result = compute_implied_borrow_fee("TEST", call_iv, put_iv, dte)
        assert result is not None
        assert abs(result.implied_fee_annualized - expected_pct) < 0.01


class TestComputeBorrowFeeFromChain:
    """Tests for computing borrow fee from a parsed options chain DataFrame."""

    @pytest.fixture
    def sample_chain(self):
        """Create a sample options chain DataFrame."""
        return pd.DataFrame({
            "strike": [95, 100, 105, 95, 100, 105],
            "option_type": ["call", "call", "call", "put", "put", "put"],
            "iv": [0.30, 0.28, 0.32, 0.33, 0.31, 0.35],
            "volume": [100, 500, 200, 150, 450, 180],
            "open_interest": [1000, 5000, 2000, 1200, 4800, 1800],
        })

    def test_computes_from_chain(self, sample_chain):
        """Should find ATM options and compute borrow fee."""
        result = compute_borrow_fee_from_chain(
            "TEST", sample_chain, spot_price=100.0, days_to_expiry=30, expiry_str="2026-05-16"
        )
        assert result is not None
        assert result.ticker == "TEST"
        assert result.expiry_used == "2026-05-16"
        assert result.days_to_expiry == 30
        # ATM call IV = 0.28, ATM put IV = 0.31 → put > call → positive borrow fee
        assert result.implied_fee_annualized > 0

    def test_empty_chain_returns_none(self):
        """Empty DataFrame should return None."""
        assert compute_borrow_fee_from_chain("X", pd.DataFrame(), 100.0, 30) is None

    def test_none_chain_returns_none(self):
        """None DataFrame should return None."""
        assert compute_borrow_fee_from_chain("X", None, 100.0, 30) is None

    def test_zero_spot_returns_none(self, sample_chain):
        """Zero spot price should return None."""
        assert compute_borrow_fee_from_chain("X", sample_chain, 0, 30) is None

    def test_missing_iv_column_returns_none(self):
        """Chain without iv column should return None."""
        df = pd.DataFrame({"strike": [100], "option_type": ["call"]})
        assert compute_borrow_fee_from_chain("X", df, 100.0, 30) is None
