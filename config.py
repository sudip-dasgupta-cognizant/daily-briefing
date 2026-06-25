"""Centralised configuration for the Daily Briefing application.

Exposes a ``Config`` dataclass that holds all user preferences and a
``load_config()`` factory that populates it from hard-coded defaults,
overriding individual fields when the corresponding env vars are present
in the ``.env`` file.

API credentials (``ANTHROPIC_API_KEY``, ``GNEWS_API_KEY``, etc.) are read
directly from the environment by each module that needs them — they are not
part of ``Config`` because they are secrets, not user preferences.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass
class Config:
    """User-facing preferences for the daily briefing.

    All fields have sensible defaults so the application works out of the
    box without any ``.env`` customisation.  Override individual fields by
    adding the corresponding variables to your ``.env`` file.

    Attributes:
        name: The listener's first name.  Used by the script generator to
            personalise the briefing.  Default: ``"Sudip"``.
        city: The listener's city.  Used for the weather lookup and as
            location context in the briefing script.  Default: ``"Kolkata"``.
        topics: Ordered list of news search topics.  The fetcher tries them
            in sequence and returns results from the first topic that yields
            articles.  Default: ``["AI", "Technology", "Finance", "Cricket"]``.
        schedule_time: The time at which the scheduler fires each day, in
            ``HH:MM`` 24-hour format (local time).  Default: ``"07:00"``.
        timezone: IANA timezone name used by the scheduler.
            Default: ``"Asia/Kolkata"``.
    """

    name: str = "Sudip"
    city: str = "Kolkata"
    topics: list[str] = field(default_factory=lambda: ["AI", "Technology", "Finance", "Cricket"])
    schedule_time: str = "07:00"
    timezone: str = "Asia/Kolkata"


def load_config() -> Config:
    """Build a ``Config`` instance from defaults, overridden by ``.env`` values.

    Reads four optional environment variables — ``BRIEFING_NAME``,
    ``BRIEFING_CITY``, ``BRIEFING_TOPICS``, and ``BRIEFING_TIME`` — and
    uses them to override the corresponding ``Config`` defaults when they
    are present and non-empty.  Fields whose env vars are absent or empty
    are left at their default values.

    ``BRIEFING_TOPICS`` is expected to be a comma-separated string; it is
    split, stripped, and filtered so that extra spaces and trailing commas
    are handled gracefully.

    Args:
        None

    Returns:
        A ``Config`` instance populated with the final resolved values.

    Raises:
        Nothing — all four env vars are optional.

    Example:
        >>> import os
        >>> os.environ["BRIEFING_NAME"] = "Priya"
        >>> os.environ["BRIEFING_CITY"] = "Mumbai"
        >>> cfg = load_config()
        >>> cfg.name
        'Priya'
        >>> cfg.city
        'Mumbai'
    """
    cfg = Config()

    if name := os.getenv("BRIEFING_NAME", "").strip():
        cfg.name = name

    if city := os.getenv("BRIEFING_CITY", "").strip():
        cfg.city = city

    if topics_raw := os.getenv("BRIEFING_TOPICS", "").strip():
        parsed = [t.strip() for t in topics_raw.split(",") if t.strip()]
        if parsed:
            cfg.topics = parsed

    if schedule_time := os.getenv("BRIEFING_TIME", "").strip():
        cfg.schedule_time = schedule_time

    return cfg
