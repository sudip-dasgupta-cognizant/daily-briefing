"""Entry point for the Daily Briefing application.

Orchestrates the full pipeline in sequence:
  1. Fetch current weather from wttr.in
  2. Fetch top news headlines from GNews
  3. Format news for the script generator
  4. Generate a spoken briefing script via Claude
  5. Convert the script to an MP3 via edge-tts
  6. Email the MP3 to the configured recipient

Run directly with:
    python main.py
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from config import load_config
from fetchers.weather import get_weather
from fetchers.news import get_news, format_news_for_script
from generator.script import generate_script
from tts.synthesize import text_to_mp3, get_output_path
from delivery.email_sender import send_briefing

load_dotenv(override=True)


def _log(message: str) -> None:
    """Print a timestamped console log line.

    Formats the current time as ``HH:MM:SS`` and prepends it to ``message``
    so every pipeline step is easy to correlate in terminal output.

    Args:
        message: The human-readable status message to print.

    Returns:
        None

    Raises:
        Nothing.

    Example:
        >>> _log("Fetching weather for Kolkata...")
        [07:01:23] Fetching weather for Kolkata...
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def run_briefing() -> None:
    """Execute the complete daily briefing pipeline end to end.

    Loads user preferences from ``config.load_config()``, then runs each
    stage in sequence, logging progress to stdout.  If any stage raises an
    exception the error is logged with full detail and the process exits
    with code ``1`` so the scheduler or a calling script can detect failure.

    Pipeline stages:
      1. **Weather** — ``fetchers.weather.get_weather(city)``
      2. **News** — ``fetchers.news.get_news(topics, api_key)``
      3. **Format** — ``fetchers.news.format_news_for_script(articles)``
      4. **Script** — ``generator.script.generate_script(name, city, weather, news)``
      5. **Output path** — ``tts.synthesize.get_output_path(name)``
      6. **TTS** — ``tts.synthesize.text_to_mp3(script, output_path)``
      7. **Email** — ``delivery.email_sender.send_briefing(mp3_path)``

    Args:
        None

    Returns:
        None

    Raises:
        SystemExit: With exit code ``1`` if any pipeline stage fails.
            The error message is printed to stdout before exiting.

    Example:
        >>> run_briefing()
    """
    cfg = load_config()
    gnews_api_key = os.getenv("GNEWS_API_KEY", "").strip()

    _log(f"Starting daily briefing for {cfg.name} in {cfg.city}")

    # Step 1 — Weather
    _log(f"Fetching weather for {cfg.city}...")
    try:
        weather_text = get_weather(cfg.city)
        _log(f"Weather OK: {weather_text[:60]}...")
    except Exception as exc:
        _log(f"ERROR fetching weather: {exc}")
        sys.exit(1)

    # Step 2 — News
    _log(f"Fetching news for topics: {cfg.topics}...")
    try:
        articles = get_news(cfg.topics, gnews_api_key)
        _log(f"News OK: {len(articles)} article(s) fetched")
    except Exception as exc:
        _log(f"ERROR fetching news: {exc}")
        sys.exit(1)

    # Step 3 — Format news
    _log("Formatting news for script generator...")
    try:
        news_text = format_news_for_script(articles)
        _log(f"Format OK: {len(articles)} story/stories ready")
    except Exception as exc:
        _log(f"ERROR formatting news: {exc}")
        sys.exit(1)

    # Step 4 — Generate script
    _log("Generating briefing script via Claude...")
    try:
        script = generate_script(cfg.name, cfg.city, weather_text, news_text)
        word_count = len(script.split())
        _log(f"Script OK: {word_count} words generated")
    except Exception as exc:
        _log(f"ERROR generating script: {exc}")
        sys.exit(1)

    # Step 5 — Output path
    _log("Resolving output path...")
    try:
        output_path = get_output_path(cfg.name)
        _log(f"Output path: {output_path}")
    except Exception as exc:
        _log(f"ERROR resolving output path: {exc}")
        sys.exit(1)

    # Step 6 — TTS
    _log("Converting script to MP3 via edge-tts...")
    try:
        mp3_path = text_to_mp3(script, output_path)
        size_kb = os.path.getsize(mp3_path) // 1024
        _log(f"TTS OK: {os.path.basename(mp3_path)} ({size_kb} KB)")
    except Exception as exc:
        _log(f"ERROR during TTS synthesis: {exc}")
        sys.exit(1)

    # Step 7 — Email
    _log(f"Sending email to {os.getenv('TO_EMAIL', '(unknown)')}...")
    try:
        send_briefing(mp3_path)
        _log("Email sent successfully")
    except Exception as exc:
        _log(f"ERROR sending email: {exc}")
        sys.exit(1)

    _log(f"Done — briefing delivered to {os.getenv('TO_EMAIL', cfg.name)}")


if __name__ == "__main__":
    run_briefing()
