"""Pre-market analysis scheduler.

Provides a simple scheduling service that triggers analysis runs at a
configurable time on trading days. Uses APScheduler if available,
falls back to a simple threading.Timer loop.

Designed to be started from the API lifespan or CLI.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, time, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class PreMarketScheduler:
    """Schedule analysis runs before market open."""

    def __init__(
        self,
        run_callback: Callable[[], None],
        schedule_time: str = "08:00",
        market_calendar: Optional[object] = None,
    ):
        self.run_callback = run_callback
        self.schedule_time = schedule_time
        self.market_calendar = market_calendar
        self._timer: Optional[threading.Timer] = None
        self._running = False

    def start(self) -> None:
        """Start the scheduler. Schedules the next run."""
        self._running = True
        self._schedule_next()
        logger.info(f"PreMarketScheduler started, target time: {self.schedule_time}")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("PreMarketScheduler stopped")

    def _schedule_next(self) -> None:
        """Schedule the next analysis run."""
        if not self._running:
            return

        now = datetime.now()
        target_time = self._parse_time(self.schedule_time)

        # Calculate next target datetime
        target_dt = now.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=0,
            microsecond=0,
        )

        # If target has passed today, schedule for tomorrow
        if target_dt <= now:
            target_dt += timedelta(days=1)

        # Skip non-trading days
        if self.market_calendar:
            while not self._is_trading_day(target_dt.date()):
                target_dt += timedelta(days=1)

        delay = (target_dt - now).total_seconds()
        logger.info(f"Next analysis scheduled for {target_dt} ({delay:.0f}s from now)")

        self._timer = threading.Timer(delay, self._execute)
        self._timer.daemon = True
        self._timer.start()

    def _execute(self) -> None:
        """Execute the scheduled run and reschedule."""
        if not self._running:
            return

        logger.info("PreMarketScheduler: triggering analysis run")
        try:
            self.run_callback()
        except Exception as e:
            logger.error(f"Scheduled analysis failed: {e}")

        # Schedule next run
        self._schedule_next()

    def _is_trading_day(self, dt) -> bool:
        """Check if a date is a trading day."""
        if self.market_calendar and hasattr(self.market_calendar, 'is_trading_day'):
            return self.market_calendar.is_trading_day(dt)
        # Fallback: weekdays only
        return dt.weekday() < 5

    @staticmethod
    def _parse_time(time_str: str) -> time:
        """Parse 'HH:MM' string to time object."""
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
