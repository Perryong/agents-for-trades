"""Pre-market analysis scheduler.

Uses APScheduler's BackgroundScheduler with CronTrigger for reliable
daily scheduling. Falls back to threading.Timer if APScheduler is unavailable.

Designed to be started from the API lifespan or CLI.
"""
from __future__ import annotations

import logging
from datetime import time
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
        self._scheduler = None
        self._running = False

    def start(self) -> None:
        """Start the scheduler."""
        target = self._parse_time(self.schedule_time)
        self._running = True

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger

            self._scheduler = BackgroundScheduler(
                job_defaults={"coalesce": True, "misfire_grace_time": 3600}
            )
            self._scheduler.add_job(
                self._execute,
                CronTrigger(
                    hour=target.hour,
                    minute=target.minute,
                    day_of_week="mon-fri",
                    timezone="US/Eastern",
                ),
                id="pre_market_analysis",
                replace_existing=True,
            )
            self._scheduler.start()
            logger.info(f"PreMarketScheduler started (APScheduler), target: {self.schedule_time} ET, Mon-Fri")

        except ImportError:
            logger.warning("APScheduler not installed, falling back to threading.Timer")
            self._start_timer_fallback(target)

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        if hasattr(self, "_timer") and self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("PreMarketScheduler stopped")

    def _execute(self) -> None:
        """Execute the scheduled run (called by APScheduler or Timer)."""
        if not self._running:
            return

        # Check trading day if calendar available
        if self.market_calendar and hasattr(self.market_calendar, "is_trading_day"):
            from datetime import date
            if not self.market_calendar.is_trading_day(date.today()):
                logger.info("Skipping analysis — not a trading day")
                return

        logger.info("PreMarketScheduler: triggering analysis run")
        try:
            self.run_callback()
        except Exception as e:
            logger.error(f"Scheduled analysis failed: {e}")

    def _start_timer_fallback(self, target: time) -> None:
        """Timer-based fallback when APScheduler is not available."""
        import threading
        from datetime import datetime, timedelta

        now = datetime.now()
        target_dt = now.replace(hour=target.hour, minute=target.minute, second=0, microsecond=0)

        if target_dt <= now:
            target_dt += timedelta(days=1)

        # Skip weekends
        while target_dt.weekday() >= 5:
            target_dt += timedelta(days=1)

        delay = (target_dt - now).total_seconds()
        logger.info(f"Next analysis (timer fallback) scheduled for {target_dt} ({delay:.0f}s)")

        self._timer = threading.Timer(delay, self._timer_execute)
        self._timer.daemon = True
        self._timer.start()

    def _timer_execute(self) -> None:
        """Timer callback — execute and reschedule."""
        self._execute()
        if self._running:
            target = self._parse_time(self.schedule_time)
            self._start_timer_fallback(target)

    @staticmethod
    def _parse_time(time_str: str) -> time:
        """Parse 'HH:MM' string to time object."""
        try:
            parts = time_str.split(":")
            return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        except (ValueError, IndexError):
            logger.warning(f"Invalid schedule_time '{time_str}', defaulting to 08:00")
            return time(8, 0)
