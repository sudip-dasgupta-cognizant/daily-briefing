"""Scheduled daily job for the Daily Briefing application.

Uses APScheduler's ``BlockingScheduler`` to trigger ``main.run_briefing``
every day at the time and timezone configured in ``config.Config``.

Run this module directly to keep the scheduler alive as a long-running
process:

    python scheduler/schedule.py

The process must remain running (e.g. in a terminal, a systemd service, or
a container) for the job to fire.  Press Ctrl+C to stop cleanly.
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import load_config
from main import run_briefing


def start_scheduler() -> None:
    """Load config, register the daily briefing job, and block until stopped.

    Parses ``config.schedule_time`` (``"HH:MM"`` format) into hour and minute
    components, creates a ``BlockingScheduler`` with the configured IANA
    timezone, and registers ``main.run_briefing`` as a cron job that fires
    every day at that time.

    Logs a startup message to stdout, then blocks.  On ``KeyboardInterrupt``
    (Ctrl+C) the scheduler is shut down gracefully and ``"Scheduler stopped."``
    is printed before the process exits.

    Args:
        None

    Returns:
        None

    Raises:
        ValueError: If ``config.schedule_time`` is not in ``"HH:MM"`` format
            or the hour/minute values are out of range.
        SystemExit: Never raised directly — ``KeyboardInterrupt`` is caught
            and converted to a clean exit.

    Example:
        >>> # Run from the command line:
        >>> # python scheduler/schedule.py
    """
    cfg = load_config()

    hour, minute = _parse_time(cfg.schedule_time)

    scheduler = BlockingScheduler(timezone=cfg.timezone)
    scheduler.add_job(
        run_briefing,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=cfg.timezone),
        name="daily_briefing",
        misfire_grace_time=300,
    )

    print(f"Scheduler started — briefing will run daily at {cfg.schedule_time} {cfg.timezone}")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)
        print("Scheduler stopped.")


def _parse_time(schedule_time: str) -> tuple[int, int]:
    """Parse a ``"HH:MM"`` time string into (hour, minute) integers.

    Args:
        schedule_time: A 24-hour time string in ``"HH:MM"`` format, e.g.
            ``"07:00"`` or ``"21:30"``.

    Returns:
        A ``(hour, minute)`` tuple of integers, e.g. ``(7, 0)``.

    Raises:
        ValueError: If ``schedule_time`` is not in ``"HH:MM"`` format, if
            it does not contain exactly one colon, or if the hour is outside
            ``0–23`` or the minute outside ``0–59``.

    Example:
        >>> _parse_time("07:30")
        (7, 30)
        >>> _parse_time("bad")
        Traceback (most recent call last):
            ...
        ValueError: schedule_time must be in HH:MM format, got 'bad'
    """
    parts = schedule_time.split(":")
    if len(parts) != 2:
        raise ValueError(f"schedule_time must be in HH:MM format, got {schedule_time!r}")

    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        raise ValueError(f"schedule_time must be in HH:MM format, got {schedule_time!r}")

    if not (0 <= hour <= 23):
        raise ValueError(f"Hour must be 0–23, got {hour}")
    if not (0 <= minute <= 59):
        raise ValueError(f"Minute must be 0–59, got {minute}")

    return hour, minute


if __name__ == "__main__":
    start_scheduler()
