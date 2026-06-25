"""Weather data fetcher using the free wttr.in JSON API.

Queries wttr.in for the current weather conditions of a given city and
returns a plain-English paragraph suitable for reading aloud in a briefing.
No API key is required — wttr.in is a free, public service.
"""

import urllib.parse
import requests


def get_weather(city: str) -> str:
    """Fetch current weather for a city and return a spoken-style summary.

    Calls ``https://wttr.in/{city}?format=j1``, extracts the key fields from
    the ``current_condition`` block, and composes a single paragraph that
    describes the temperature, sky condition, humidity, wind, and a
    context-appropriate tip (umbrella, sun protection, etc.).

    If the API is unreachable or returns unexpected data, a safe fallback
    string is returned instead of raising so the broader pipeline can
    continue without weather data.

    Args:
        city: The city name or location string to look up, e.g. ``"Kolkata"``
            or ``"New York"``.  Spaces and special characters are
            URL-encoded automatically.

    Returns:
        A plain-English paragraph of two to three sentences, e.g.:
        ``"It's currently 31°C in Kolkata, feels like 36°C. Expect partly
        cloudy skies with humidity at 78% and winds at 12 km/h. Carry an
        umbrella if you're heading out."``

        On any error the return value is a human-readable fallback string
        that is safe to include in a spoken briefing.

    Raises:
        Nothing — all exceptions are caught internally and converted to the
        fallback string so the pipeline never hard-stops on weather failure.

    Example:
        >>> summary = get_weather("Kolkata")
        >>> summary.startswith("It's currently")
        True
    """
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data["current_condition"][0]
        condition: str = current["weatherDesc"][0]["value"]
        temp_c: str = current["temp_C"]
        feels_like_c: str = current["FeelsLikeC"]
        humidity: str = current["humidity"]
        wind_kmph: str = current["windspeedKmph"]

        tip = _contextual_tip(condition, int(temp_c))

        return (
            f"It's currently {temp_c}°C in {city}, feels like {feels_like_c}°C. "
            f"Expect {condition.lower()} skies with humidity at {humidity}% "
            f"and winds at {wind_kmph} km/h. {tip}"
        )

    except requests.exceptions.Timeout:
        return (
            f"Weather data for {city} is unavailable right now "
            "(request timed out). Skipping weather in today's briefing."
        )
    except requests.exceptions.ConnectionError:
        return (
            f"Weather data for {city} is unavailable right now "
            "(could not reach wttr.in). Skipping weather in today's briefing."
        )
    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "unknown"
        return (
            f"Weather data for {city} is unavailable right now "
            f"(HTTP {code}). Skipping weather in today's briefing."
        )
    except (KeyError, IndexError, ValueError):
        return (
            f"Weather data for {city} returned an unexpected format. "
            "Skipping weather in today's briefing."
        )


def _contextual_tip(condition: str, temp_c: int) -> str:
    """Return a one-sentence weather tip based on condition and temperature.

    Chooses the most relevant practical advice for the listener: rain gear,
    cold-weather precautions, heat warnings, or a general comfort note.

    Args:
        condition: The human-readable condition string from wttr.in, e.g.
            ``"Partly cloudy"`` or ``"Heavy rain"``.
        temp_c: The current temperature in Celsius as an integer.

    Returns:
        A single sentence ending with a full stop, e.g.
        ``"Carry an umbrella if you're heading out."``

    Raises:
        Nothing.

    Example:
        >>> _contextual_tip("Heavy rain", 22)
        "Carry an umbrella if you're heading out."
        >>> _contextual_tip("Clear", 38)
        'Stay hydrated and avoid prolonged sun exposure.'
    """
    c = condition.lower()
    if any(word in c for word in ("rain", "drizzle", "shower", "thunder", "storm")):
        return "Carry an umbrella if you're heading out."
    if any(word in c for word in ("snow", "blizzard", "sleet", "ice")):
        return "Bundle up and watch for slippery conditions."
    if any(word in c for word in ("fog", "mist", "haze")):
        return "Allow extra travel time and drive with caution."
    if temp_c >= 35:
        return "Stay hydrated and avoid prolonged sun exposure."
    if temp_c <= 5:
        return "Dress in warm layers before stepping out."
    return "Dress comfortably and enjoy the day."
