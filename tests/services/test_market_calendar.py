"""Tests for MarketCalendar service (Epic 8, Story 8.5)."""
from datetime import date

import pytest

from tradingagents.services.market_calendar import MarketCalendar


@pytest.fixture
def cal():
    return MarketCalendar()


class TestMarketCalendar:
    def test_weekday_is_trading_day(self, cal):
        # 2026-04-13 is a Monday
        assert cal.is_trading_day(date(2026, 4, 13)) is True

    def test_weekend_is_not_trading_day(self, cal):
        # 2026-04-11 is a Saturday
        assert cal.is_trading_day(date(2026, 4, 11)) is False
        # 2026-04-12 is a Sunday
        assert cal.is_trading_day(date(2026, 4, 12)) is False

    def test_christmas_is_not_trading_day(self, cal):
        assert cal.is_trading_day(date(2025, 12, 25)) is False

    def test_new_years_is_not_trading_day(self, cal):
        assert cal.is_trading_day(date(2026, 1, 1)) is False

    def test_mlk_day_is_not_trading_day(self, cal):
        # MLK Day 2026 is January 19
        assert cal.is_trading_day(date(2026, 1, 19)) is False

    def test_market_open_time(self, cal):
        t = cal.market_open_time(date(2026, 4, 13))
        assert t is not None
        assert t.hour == 13 or t.hour == 14  # UTC: 9:30 ET = 13:30 or 14:30 UTC depending on DST

    def test_market_close_time(self, cal):
        t = cal.market_close_time(date(2026, 4, 13))
        assert t is not None

    def test_market_open_time_non_trading_day(self, cal):
        assert cal.market_open_time(date(2026, 4, 11)) is None

    def test_next_trading_day_from_friday(self, cal):
        # 2026-04-10 is a Friday
        nxt = cal.next_trading_day(date(2026, 4, 10))
        assert nxt == date(2026, 4, 13)  # Monday

    def test_next_trading_day_from_wednesday(self, cal):
        nxt = cal.next_trading_day(date(2026, 4, 8))
        assert nxt == date(2026, 4, 9)  # Thursday

    def test_previous_trading_day_from_monday(self, cal):
        prev = cal.previous_trading_day(date(2026, 4, 13))
        assert prev == date(2026, 4, 10)  # Friday

    def test_trading_days_in_range(self, cal):
        days = cal.trading_days_in_range(date(2026, 4, 6), date(2026, 4, 10))
        assert len(days) == 5  # Mon-Fri full week
        assert all(d.weekday() < 5 for d in days)

    def test_trading_days_excludes_weekend(self, cal):
        days = cal.trading_days_in_range(date(2026, 4, 10), date(2026, 4, 13))
        # Fri + Mon = 2 days
        assert len(days) == 2
