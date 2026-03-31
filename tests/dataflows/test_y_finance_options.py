"""Unit tests for yfinance options fallback module (y_finance_options.py).

All yfinance calls are mocked — no network access required.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd


class TestGetOptionsExpirations(unittest.TestCase):
    """Tests for get_options_expirations."""

    def test_get_options_expirations(self):
        """Mocked yf.Ticker returns .options tuple; function returns list of date strings."""
        mock_ticker = MagicMock()
        mock_ticker.options = ("2026-01-17", "2026-02-21", "2026-03-21")

        with patch("yfinance.Ticker", return_value=mock_ticker):
            from tradingagents.dataflows.y_finance_options import get_options_expirations
            result = get_options_expirations("AAPL")

        self.assertIsInstance(result, list)
        self.assertEqual(result, ["2026-01-17", "2026-02-21", "2026-03-21"])

    def test_get_options_expirations_no_options(self):
        """Mocked yf.Ticker returns empty .options tuple; function returns empty list."""
        mock_ticker = MagicMock()
        mock_ticker.options = ()

        with patch("yfinance.Ticker", return_value=mock_ticker):
            from tradingagents.dataflows.y_finance_options import get_options_expirations
            result = get_options_expirations("AAPL")

        self.assertIsInstance(result, list)
        self.assertEqual(result, [])


class TestGetOptionsChain(unittest.TestCase):
    """Tests for get_options_chain."""

    def _make_chain_df(self):
        """Create a minimal DataFrame matching yfinance option_chain output."""
        data = {
            "strike": [150.0, 155.0],
            "bid": [2.10, 1.50],
            "ask": [2.20, 1.60],
            "volume": [100, 200],
            "openInterest": [500, 600],
            "impliedVolatility": [0.25, 0.30],
            "contractSymbol": ["AAPL260117C00150000", "AAPL260117C00155000"],
            "lastTradeDate": [pd.Timestamp("2026-01-10"), pd.Timestamp("2026-01-10")],
            "lastPrice": [2.15, 1.55],
            "change": [0.05, -0.10],
            "percentChange": [2.3, -6.1],
            "inTheMoney": [True, False],
            "contractSize": ["REGULAR", "REGULAR"],
            "currency": ["USD", "USD"],
        }
        return pd.DataFrame(data)

    def test_get_options_chain_columns(self):
        """Output string contains renamed columns: strike, bid, ask, volume, open_interest, iv."""
        calls_df = self._make_chain_df()
        puts_df = self._make_chain_df()

        mock_chain = MagicMock()
        mock_chain.calls = calls_df
        mock_chain.puts = puts_df

        mock_ticker = MagicMock()
        mock_ticker.option_chain.return_value = mock_chain

        with patch("yfinance.Ticker", return_value=mock_ticker), \
             patch("tradingagents.dataflows.y_finance_options.get_cached_text",
                   side_effect=lambda **kwargs: kwargs["fetcher"]()):
            from tradingagents.dataflows.y_finance_options import get_options_chain
            result = get_options_chain("AAPL", "2026-01-17")

        self.assertIn("strike", result)
        self.assertIn("bid", result)
        self.assertIn("ask", result)
        self.assertIn("volume", result)
        self.assertIn("open_interest", result)
        self.assertIn("iv", result)

    def test_get_options_chain_no_greeks(self):
        """Output string for chain contains None values for delta, gamma, theta, vega columns."""
        calls_df = self._make_chain_df()
        puts_df = self._make_chain_df()

        mock_chain = MagicMock()
        mock_chain.calls = calls_df
        mock_chain.puts = puts_df

        mock_ticker = MagicMock()
        mock_ticker.option_chain.return_value = mock_chain

        with patch("yfinance.Ticker", return_value=mock_ticker), \
             patch("tradingagents.dataflows.y_finance_options.get_cached_text",
                   side_effect=lambda **kwargs: kwargs["fetcher"]()):
            from tradingagents.dataflows.y_finance_options import get_options_chain
            result = get_options_chain("AAPL", "2026-01-17")

        # delta, gamma, theta, vega columns should exist and contain None values
        self.assertIn("delta", result)
        self.assertIn("gamma", result)
        self.assertIn("theta", result)
        self.assertIn("vega", result)
        self.assertIn("None", result)


class TestGetHistoricalIV(unittest.TestCase):
    """Tests for get_historical_iv."""

    def _make_chain_df(self, iv_value: float = 0.25):
        """Create a minimal calls DataFrame for option_chain."""
        return pd.DataFrame({
            "strike": [150.0, 155.0, 160.0],
            "bid": [2.10, 1.50, 1.00],
            "ask": [2.20, 1.60, 1.10],
            "volume": [100, 200, 150],
            "openInterest": [500, 600, 400],
            "impliedVolatility": [iv_value, iv_value + 0.02, iv_value - 0.01],
            "contractSymbol": ["C1", "C2", "C3"],
            "lastTradeDate": [pd.Timestamp("2026-01-10")] * 3,
            "lastPrice": [2.15, 1.55, 1.05],
            "change": [0.05, -0.10, 0.02],
            "percentChange": [2.3, -6.1, 1.9],
            "inTheMoney": [True, False, False],
            "contractSize": ["REGULAR"] * 3,
            "currency": ["USD"] * 3,
        })

    def test_get_historical_iv(self):
        """Mocked ticker with multiple expirations; output string contains 'date' and 'iv'."""
        calls_df = self._make_chain_df(0.25)
        puts_df = self._make_chain_df(0.27)

        mock_chain = MagicMock()
        mock_chain.calls = calls_df
        mock_chain.puts = puts_df

        mock_ticker = MagicMock()
        mock_ticker.options = ("2026-01-17", "2026-02-21")
        mock_ticker.option_chain.return_value = mock_chain

        with patch("yfinance.Ticker", return_value=mock_ticker), \
             patch("tradingagents.dataflows.y_finance_options.get_cached_text",
                   side_effect=lambda **kwargs: kwargs["fetcher"]()):
            from tradingagents.dataflows.y_finance_options import get_historical_iv
            result = get_historical_iv("AAPL", weeks=4)

        self.assertIn("date", result)
        self.assertIn("iv", result)

    def test_get_historical_iv_empty(self):
        """Mocked ticker with no expirations returns 'No historical IV data' message."""
        mock_ticker = MagicMock()
        mock_ticker.options = ()

        with patch("yfinance.Ticker", return_value=mock_ticker), \
             patch("tradingagents.dataflows.y_finance_options.get_cached_text",
                   side_effect=lambda **kwargs: kwargs["fetcher"]()):
            from tradingagents.dataflows.y_finance_options import get_historical_iv
            result = get_historical_iv("AAPL", weeks=4)

        self.assertIn("No historical IV data", result)


if __name__ == "__main__":
    unittest.main()
