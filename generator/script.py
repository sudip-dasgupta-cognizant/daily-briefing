"""Briefing script generator powered by the Anthropic Claude API.

Takes a person's name, city, pre-formatted weather text, and pre-formatted
news text, then calls Claude to produce a warm, personalised, radio-style
morning briefing in flowing prose — ready for TTS synthesis.
"""

import anthropic
from datetime import date
from dotenv import load_dotenv
import os

load_dotenv(override=True)

_SYSTEM_PROMPT = (
    "You are a warm, upbeat morning radio host for an Indian audience. "
    "You speak directly to one person by name. Your tone is conversational, "
    "friendly, and energetic — like a smart friend giving you the morning "
    "rundown. Never use bullet points. Always use flowing prose."
)


def generate_script(
    name: str,
    city: str,
    weather_text: str,
    news_text: str,
) -> str:
    """Generate a personalised 5-minute morning briefing script using Claude.

    Constructs a structured user prompt from the supplied data, sends it to
    ``claude-sonnet-4-6`` with a fixed radio-host system prompt, and returns
    the raw text content of the model's reply.  The script has three sections
    — weather, news, and a closing idea — all written as natural prose.

    Args:
        name: The listener's first name, e.g. ``"Sudip"``.  Used throughout
            the script so the briefing feels personal.
        city: The listener's city, e.g. ``"Kolkata"``.  Included in the
            weather and greeting sections.
        weather_text: The pre-formatted weather paragraph produced by
            ``fetchers.weather.get_weather``.  Passed verbatim into the
            prompt so Claude can weave it into natural speech.
        news_text: The pre-formatted news block produced by
            ``fetchers.news.format_news_for_script``.  Each story is on its
            own line as ``"Story N: {title} — {summary} (Source: {source})"``.

    Returns:
        A plain-text string containing the full briefing script.  The script
        uses no markdown, no bullet points, and no section headers — only
        flowing prose ready for TTS synthesis.  Typically 450–600 words
        (roughly 3–4 minutes at a natural speaking pace).

    Raises:
        anthropic.APIConnectionError: If the Anthropic API cannot be reached.
        anthropic.AuthenticationError: If the ``ANTHROPIC_API_KEY`` environment
            variable is missing or invalid.
        anthropic.RateLimitError: If the account's API rate limit is exceeded.

    Example:
        >>> script = generate_script(
        ...     name="Sudip",
        ...     city="Kolkata",
        ...     weather_text="It's currently 31°C in Kolkata, feels like 36°C...",
        ...     news_text="Story 1: AI beats chess record — DeepMind's... (Source: TechCrunch)",
        ... )
        >>> "Sudip" in script
        True
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise anthropic.AuthenticationError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )

    _d = date.today()
    today = f"{_d.strftime('%A')}, {_d.day} {_d.strftime('%B %Y')}"

    user_prompt = _build_user_prompt(name, city, today, weather_text, news_text)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text


def _build_user_prompt(
    name: str,
    city: str,
    today: str,
    weather_text: str,
    news_text: str,
) -> str:
    """Compose the structured user prompt sent to Claude.

    Inlines all runtime data into a fixed template so the model always
    receives instructions and data in a consistent format.

    Args:
        name: The listener's first name.
        city: The listener's city.
        today: Today's date formatted as ``"Monday, 25 June 2026"``.
        weather_text: Pre-formatted weather paragraph.
        news_text: Pre-formatted numbered news block.

    Returns:
        A multi-line string ready to be sent as the ``user`` turn in the
        Claude Messages API call.

    Raises:
        Nothing.

    Example:
        >>> prompt = _build_user_prompt("Sudip", "Kolkata", "Thursday, 25 June 2026",
        ...                             "It's 31°C...", "Story 1: Foo — Bar. (Source: BBC)")
        >>> "Sudip" in prompt and "Kolkata" in prompt
        True
    """
    return f"""Generate a personalized 5-minute morning briefing script for {name} in {city}. Today's date is {today}.

Use exactly this structure:

WEATHER: Use this data: {weather_text}. Write 2-3 natural sentences.

NEWS: Use these stories: {news_text}. Introduce each story naturally, give context, make it feel current. 3 stories, 2-3 sentences each.

IDEA: End with one interesting idea, insight, or quote relevant to someone working in AI and technology. 3-4 sentences. Make it genuinely thought-provoking.

Address {name} directly by name at least twice throughout the script. Do not use any bullet points, headers, or markdown. Write everything as warm, flowing spoken prose."""
