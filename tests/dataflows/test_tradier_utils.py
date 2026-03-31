"""Unit tests for tradingagents.dataflows.tradier_utils.

All tests use unittest.mock to mock requests.get and os.environ.
No network calls are made.
"""
import os
from unittest.mock import MagicMock, patch

import pytest
import requests


# ---------------------------------------------------------------------------
# _get_api_key
# ---------------------------------------------------------------------------

def test_get_api_key_returns_env_value():
    """_get_api_key() returns the value of TRADIER_API_KEY when set."""
    from tradingagents.dataflows.tradier_utils import _get_api_key

    with patch.dict(os.environ, {"TRADIER_API_KEY": "test-key-123"}):
        assert _get_api_key() == "test-key-123"


def test_get_api_key_raises_without_env():
    """_get_api_key() raises ValueError containing 'TRADIER_API_KEY' when unset."""
    from tradingagents.dataflows.tradier_utils import _get_api_key

    env = {k: v for k, v in os.environ.items() if k != "TRADIER_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="TRADIER_API_KEY"):
            _get_api_key()


# ---------------------------------------------------------------------------
# _get_base_url
# ---------------------------------------------------------------------------

def test_get_base_url_sandbox():
    """With TRADIER_SANDBOX='true', _get_base_url() returns the sandbox URL."""
    from tradingagents.dataflows.tradier_utils import _get_base_url

    with patch.dict(os.environ, {"TRADIER_SANDBOX": "true"}):
        url = _get_base_url()
    assert url == "https://sandbox.tradier.com/v1"


def test_get_base_url_production():
    """With TRADIER_SANDBOX unset, _get_base_url() returns the sandbox URL (safe default)."""
    from tradingagents.dataflows.tradier_utils import _get_base_url

    env = {k: v for k, v in os.environ.items() if k != "TRADIER_SANDBOX"}
    with patch.dict(os.environ, env, clear=True):
        url = _get_base_url()
    assert url == "https://sandbox.tradier.com/v1"


# ---------------------------------------------------------------------------
# _make_request
# ---------------------------------------------------------------------------

def _mock_response(status_code: int, json_data: dict | None = None, headers: dict | None = None):
    """Helper that returns a MagicMock mimicking a requests.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.headers = headers or {}
    if json_data is not None:
        mock_resp.json.return_value = json_data
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_resp
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_make_request_auth_header():
    """_make_request sends Authorization: Bearer <key> header."""
    from tradingagents.dataflows.tradier_utils import _make_request

    mock_resp = _mock_response(200, {"data": "ok"})
    with patch("requests.get", return_value=mock_resp) as mock_get, \
         patch.dict(os.environ, {"TRADIER_API_KEY": "test-key", "TRADIER_SANDBOX": "true"}):
        _make_request("/markets/options/expirations", {"symbol": "AAPL"})
        call_kwargs = mock_get.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers") or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
        # Also try positional
        if not headers and len(call_kwargs[0]) >= 1:
            headers = {}
        # Extract headers from whatever form they came in
        all_kwargs = mock_get.call_args[1] if mock_get.call_args[1] else {}
        h = all_kwargs.get("headers", {})
        assert h.get("Authorization") == "Bearer test-key"


def test_make_request_rate_limit():
    """_make_request raises TradierRateLimitError on HTTP 429."""
    from tradingagents.dataflows.tradier_utils import _make_request, TradierRateLimitError

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {"X-Ratelimit-Available": "0"}
    mock_resp.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_resp), \
         patch.dict(os.environ, {"TRADIER_API_KEY": "test-key", "TRADIER_SANDBOX": "true"}):
        with pytest.raises(TradierRateLimitError):
            _make_request("/markets/options/expirations", {"symbol": "AAPL"})


def test_make_request_other_error():
    """_make_request raises requests.exceptions.HTTPError on HTTP 404 (not TradierRateLimitError)."""
    from tradingagents.dataflows.tradier_utils import _make_request, TradierRateLimitError

    mock_resp = _mock_response(404)

    with patch("requests.get", return_value=mock_resp), \
         patch.dict(os.environ, {"TRADIER_API_KEY": "test-key", "TRADIER_SANDBOX": "true"}):
        with pytest.raises(requests.exceptions.HTTPError):
            _make_request("/markets/options/expirations", {"symbol": "AAPL"})

        # Must NOT be a TradierRateLimitError
        try:
            _make_request("/markets/options/expirations", {"symbol": "AAPL"})
        except TradierRateLimitError:
            pytest.fail("Should not raise TradierRateLimitError for 404")
        except requests.exceptions.HTTPError:
            pass


# ---------------------------------------------------------------------------
# get_options_expirations
# ---------------------------------------------------------------------------

def test_get_options_expirations_returns_list(mock_tradier_expirations_response):
    """get_options_expirations returns a list of date strings."""
    from tradingagents.dataflows.tradier_utils import get_options_expirations

    mock_resp = _mock_response(200, mock_tradier_expirations_response)
    with patch("requests.get", return_value=mock_resp), \
         patch.dict(os.environ, {"TRADIER_API_KEY": "test-key", "TRADIER_SANDBOX": "true"}):
        result = get_options_expirations("AAPL")
    assert isinstance(result, list)
    assert "2024-01-19" in result
    assert len(result) == 3


def test_get_options_expirations_null():
    """get_options_expirations returns empty list when expirations is null."""
    from tradingagents.dataflows.tradier_utils import get_options_expirations

    mock_resp = _mock_response(200, {"expirations": None})
    with patch("requests.get", return_value=mock_resp), \
         patch.dict(os.environ, {"TRADIER_API_KEY": "test-key", "TRADIER_SANDBOX": "true"}):
        result = get_options_expirations("AAPL")
    assert result == []


def test_get_options_expirations_single_date():
    """get_options_expirations normalizes single string date to list of one."""
    from tradingagents.dataflows.tradier_utils import get_options_expirations

    mock_resp = _mock_response(200, {"expirations": {"date": "2024-01-19"}})
    with patch("requests.get", return_value=mock_resp), \
         patch.dict(os.environ, {"TRADIER_API_KEY": "test-key", "TRADIER_SANDBOX": "true"}):
        result = get_options_expirations("AAPL")
    assert result == ["2024-01-19"]


# ---------------------------------------------------------------------------
# get_options_chain
# ---------------------------------------------------------------------------

def test_get_options_chain_returns_dataframe_str(mock_tradier_chain_response):
    """get_options_chain returns a string containing all required column names."""
    from tradingagents.dataflows.tradier_utils import get_options_chain

    required_columns = [
        "strike", "expiration_date", "bid", "ask", "volume",
        "open_interest", "delta", "gamma", "theta", "vega", "iv",
    ]
    mock_resp = _mock_response(200, mock_tradier_chain_response)
    with patch("requests.get", return_value=mock_resp), \
         patch.dict(os.environ, {"TRADIER_API_KEY": "test-key", "TRADIER_SANDBOX": "true"}), \
         patch("tradingagents.dataflows.tradier_utils.get_cached_text", side_effect=lambda **kw: kw["fetcher"]()):
        result = get_options_chain("AAPL", "2024-01-19")
    assert isinstance(result, str)
    for col in required_columns:
        assert col in result, f"Column '{col}' not found in result string"


def test_get_options_chain_single_contract(mock_tradier_single_contract_response):
    """get_options_chain handles single-contract response (dict, not list)."""
    from tradingagents.dataflows.tradier_utils import get_options_chain

    mock_resp = _mock_response(200, mock_tradier_single_contract_response)
    with patch("requests.get", return_value=mock_resp), \
         patch.dict(os.environ, {"TRADIER_API_KEY": "test-key", "TRADIER_SANDBOX": "true"}), \
         patch("tradingagents.dataflows.tradier_utils.get_cached_text", side_effect=lambda **kw: kw["fetcher"]()):
        result = get_options_chain("AAPL", "2024-01-19")
    assert isinstance(result, str)
    # Should not crash and should return tabular data
    assert "150" in result


def test_get_options_chain_null_greeks(mock_tradier_null_greeks_response):
    """get_options_chain handles null greeks (None values, no crash)."""
    from tradingagents.dataflows.tradier_utils import get_options_chain

    mock_resp = _mock_response(200, mock_tradier_null_greeks_response)
    with patch("requests.get", return_value=mock_resp), \
         patch.dict(os.environ, {"TRADIER_API_KEY": "test-key", "TRADIER_SANDBOX": "true"}), \
         patch("tradingagents.dataflows.tradier_utils.get_cached_text", side_effect=lambda **kw: kw["fetcher"]()):
        # Should not raise any exception
        result = get_options_chain("AAPL", "2024-01-19")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# get_historical_iv
# ---------------------------------------------------------------------------

def test_get_historical_iv_returns_dataframe_str(mock_tradier_chain_response):
    """get_historical_iv returns a string with date and iv data."""
    from tradingagents.dataflows.tradier_utils import get_historical_iv

    # Mock expirations and chain calls
    expiration_data = {"expirations": {"date": ["2024-01-19", "2024-02-16"]}}
    exp_resp = _mock_response(200, expiration_data)
    chain_resp = _mock_response(200, mock_tradier_chain_response)

    def side_effect(url, **kwargs):
        if "expirations" in url:
            return exp_resp
        return chain_resp

    with patch("requests.get", side_effect=side_effect), \
         patch.dict(os.environ, {"TRADIER_API_KEY": "test-key", "TRADIER_SANDBOX": "true"}), \
         patch("tradingagents.dataflows.tradier_utils.get_cached_text", side_effect=lambda **kw: kw["fetcher"]()):
        result = get_historical_iv("AAPL", weeks=52)
    assert isinstance(result, str)
    # Should contain date and iv columns or no-data message
    assert ("date" in result and "iv" in result) or "No historical IV" in result
