"""Market calendar service wrapping exchange_calendars.

Injectable dependency for testability. Provides trading day queries
for the risk judge and pipeline scheduling.

Earnings/ex-dividend date integration deferred to Phase 2.
"""
from datetime import date, datetime, time
from typing import Optional

import exchange_calendars as xcals
import pandas as pd


class MarketCalendar:
    """NYSE market calendar wrapper."""

    def __init__(self, exchange: str = "XNYS"):
        self._cal = xcals.get_calendar(exchange)

    def is_trading_day(self, dt: date) -> bool:
        """Return True if the given date is a regular trading day."""
        ts = pd.Timestamp(dt)
        return self._cal.is_session(ts)

    def market_open_time(self, dt: date) -> Optional[time]:
        """Return market open time for the given trading day, or None if not a trading day."""
        ts = pd.Timestamp(dt)
        if not self._cal.is_session(ts):
            return None
        return self._cal.session_open(ts).time()

    def market_close_time(self, dt: date) -> Optional[time]:
        """Return market close time for the given trading day, or None if not a trading day."""
        ts = pd.Timestamp(dt)
        if not self._cal.is_session(ts):
            return None
        return self._cal.session_close(ts).time()

    def next_trading_day(self, dt: date) -> date:
        """Return the next trading day after the given date."""
        ts = pd.Timestamp(dt)
        sessions = self._cal.sessions_in_range(
            ts + pd.Timedelta(days=1),
            ts + pd.Timedelta(days=10),
        )
        return sessions[0].date()

    def previous_trading_day(self, dt: date) -> date:
        """Return the most recent trading day before the given date."""
        ts = pd.Timestamp(dt)
        sessions = self._cal.sessions_in_range(
            ts - pd.Timedelta(days=10),
            ts - pd.Timedelta(days=1),
        )
        return sessions[-1].date()

    def trading_days_in_range(self, start: date, end: date) -> list[date]:
        """Return all trading days between start and end (inclusive)."""
        sessions = self._cal.sessions_in_range(
            pd.Timestamp(start), pd.Timestamp(end)
        )
        return [s.date() for s in sessions]
