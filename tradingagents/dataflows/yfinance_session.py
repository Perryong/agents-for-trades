"""Shared yfinance session with optional proxy support.

If the ``YFINANCE_PROXY`` environment variable is set, all yfinance requests
will be routed through that proxy.  This is required in networks where
``query2.finance.yahoo.com`` is blocked or unresolvable.

Usage::

    from .yfinance_session import yf_session

    ticker = yf.Ticker("AAPL", session=yf_session())
    yf.download("AAPL", session=yf_session())
"""
from __future__ import annotations

import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session: requests.Session | None = None


def yf_session() -> requests.Session | None:
    """Return a shared ``requests.Session`` configured with proxy/retry, or
    ``None`` when no proxy is needed (yfinance uses its own defaults)."""
    global _session

    proxy = os.environ.get("YFINANCE_PROXY")
    if not proxy:
        return None  # Let yfinance use its defaults

    if _session is not None:
        return _session

    _session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    _session.mount("https://", adapter)
    _session.mount("http://", adapter)
    _session.proxies = {"https": proxy, "http": proxy}
    return _session
