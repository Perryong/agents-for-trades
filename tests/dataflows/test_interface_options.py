"""Tests for options routing in tradingagents.dataflows.interface."""

import pytest
from unittest.mock import patch, MagicMock

from tradingagents.dataflows.interface import (
    TOOLS_CATEGORIES,
    VENDOR_LIST,
    VENDOR_METHODS,
    route_to_vendor,
    get_category_for_method,
)
from tradingagents.dataflows.tradier_utils import TradierRateLimitError


def test_options_data_in_tools_categories():
    assert "options_data" in TOOLS_CATEGORIES
    tools = TOOLS_CATEGORIES["options_data"]["tools"]
    assert "get_options_expirations" in tools
    assert "get_options_chain" in tools
    assert "get_historical_iv" in tools


def test_tradier_in_vendor_list():
    assert "tradier" in VENDOR_LIST


def test_vendor_methods_has_options_expirations():
    assert "get_options_expirations" in VENDOR_METHODS
    assert "tradier" in VENDOR_METHODS["get_options_expirations"]
    assert "yfinance" in VENDOR_METHODS["get_options_expirations"]


def test_vendor_methods_has_options_chain():
    assert "get_options_chain" in VENDOR_METHODS
    assert "tradier" in VENDOR_METHODS["get_options_chain"]
    assert "yfinance" in VENDOR_METHODS["get_options_chain"]


def test_vendor_methods_has_historical_iv():
    assert "get_historical_iv" in VENDOR_METHODS
    assert "tradier" in VENDOR_METHODS["get_historical_iv"]
    assert "yfinance" in VENDOR_METHODS["get_historical_iv"]


def test_route_to_vendor_options_chain():
    """route_to_vendor calls tradier implementation when tradier is configured."""
    mock_result = "mock options chain data"
    tradier_func = VENDOR_METHODS["get_options_chain"]["tradier"]
    target = f"tradingagents.dataflows.interface.VENDOR_METHODS"

    with patch.dict(
        "tradingagents.dataflows.interface.VENDOR_METHODS",
        {
            "get_options_chain": {
                "tradier": MagicMock(return_value=mock_result),
                "yfinance": MagicMock(return_value="yfinance fallback"),
            }
        },
    ):
        with patch(
            "tradingagents.dataflows.interface.get_vendor",
            return_value="tradier",
        ):
            result = route_to_vendor("get_options_chain", "AAPL", "2026-01-17")
    assert result == mock_result


def test_tradier_rate_limit_fallback():
    """When tradier raises TradierRateLimitError, route_to_vendor falls back to yfinance."""
    yfinance_result = "yfinance fallback data"
    tradier_mock = MagicMock(side_effect=TradierRateLimitError("rate limited"))
    yfinance_mock = MagicMock(return_value=yfinance_result)

    with patch.dict(
        "tradingagents.dataflows.interface.VENDOR_METHODS",
        {
            "get_options_chain": {
                "tradier": tradier_mock,
                "yfinance": yfinance_mock,
            }
        },
    ):
        with patch(
            "tradingagents.dataflows.interface.get_vendor",
            return_value="tradier",
        ):
            result = route_to_vendor("get_options_chain", "AAPL", "2026-01-17")

    assert result == yfinance_result
    tradier_mock.assert_called_once_with("AAPL", "2026-01-17")
    yfinance_mock.assert_called_once_with("AAPL", "2026-01-17")


def test_get_category_for_options_method():
    assert get_category_for_method("get_options_chain") == "options_data"
