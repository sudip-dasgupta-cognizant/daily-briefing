"""News headline fetcher using the GNews API.

Retrieves the top N headlines for a list of topics from the GNews /search
endpoint and returns them as a normalised list of article dicts ready for
the script generator.

GNews free tier allows 100 requests per day — more than sufficient for a
once-daily briefing that makes at most one successful request per run.
"""

import requests


_GNEWS_SEARCH_URL = "https://gnews.io/api/v4/search"


def get_news(topics: list[str], api_key: str, count: int = 3) -> list[dict]:
    """Fetch top news articles for the first topic that returns results.

    Iterates through ``topics`` in order, calling the GNews ``/search``
    endpoint for each one.  Returns as soon as a topic yields at least one
    article.  If every topic fails (API error or empty result set) an empty
    list is returned so the pipeline can continue without news data.

    Args:
        topics: Ordered list of search topics to try, e.g.
            ``["technology", "world news", "business"]``.  The first topic
            that returns results wins; remaining topics are skipped.
        api_key: A valid GNews API key.  Passed as the ``apikey`` query
            parameter.
        count: Maximum number of articles to return per topic.  GNews free
            tier supports up to 10 per request.  Defaults to ``3``.

    Returns:
        A list of up to ``count`` article dicts, each containing exactly:

        - ``title`` (str): The article headline.
        - ``summary`` (str): One-sentence description from the API's
          ``description`` field; falls back to ``title`` if description is
          empty.
        - ``source`` (str): The publishing outlet name.

        Returns an empty list if every topic fails or returns no articles.

    Raises:
        Nothing — all exceptions are caught internally and trigger a
        fallback to the next topic (or an empty list if none remain).

    Example:
        >>> articles = get_news(["technology"], api_key="YOUR_KEY", count=2)
        >>> articles[0]["title"]
        'OpenAI announces new model'
    """
    for topic in topics:
        try:
            articles = _fetch_topic(topic, api_key, count)
            if articles:
                return articles
        except Exception:
            continue
    return []


def format_news_for_script(articles: list[dict]) -> str:
    """Format a list of article dicts into a numbered plain-text block.

    Produces a multi-line string where each line follows the pattern
    ``"Story N: {title} — {summary} (Source: {source})"``.  Designed to
    be embedded directly into a Claude prompt or a spoken briefing script.

    Args:
        articles: A list of article dicts as returned by ``get_news``.
            Each dict must contain ``title``, ``summary``, and ``source``
            keys.  An empty list is handled gracefully.

    Returns:
        A newline-separated string of numbered stories, e.g.::

            Story 1: OpenAI announces new model — The company unveiled... (Source: TechCrunch)
            Story 2: Markets rebound — Stocks rose sharply... (Source: Reuters)

        If ``articles`` is empty, returns the string
        ``"No news stories available today."``.

    Raises:
        Nothing.

    Example:
        >>> arts = [{"title": "Foo", "summary": "Bar.", "source": "BBC"}]
        >>> format_news_for_script(arts)
        'Story 1: Foo — Bar. (Source: BBC)'
    """
    if not articles:
        return "No news stories available today."

    lines = [
        f"Story {i}: {a['title']} — {a['summary']} (Source: {a['source']})"
        for i, a in enumerate(articles, start=1)
    ]
    return "\n".join(lines)


def _fetch_topic(topic: str, api_key: str, count: int) -> list[dict]:
    """Call the GNews /search endpoint for a single topic and normalise results.

    Sends a GET request with ``q``, ``lang``, ``country``, ``max``, and
    ``apikey`` parameters.  Raises on any HTTP or network error so the
    caller (``get_news``) can decide whether to try the next topic.

    Args:
        topic: The search query string, e.g. ``"technology"``.
        api_key: A valid GNews API key.
        count: Maximum number of articles to request (``max`` parameter).

    Returns:
        A list of normalised article dicts (``title``, ``summary``,
        ``source``).  Returns an empty list if the API response contains no
        articles.

    Raises:
        requests.HTTPError: If the API returns a non-2xx status code.
        requests.ConnectionError: If the network request fails.
        requests.Timeout: If the request exceeds 10 seconds.
        KeyError: If the response JSON is missing expected fields.

    Example:
        >>> _fetch_topic("business", "YOUR_KEY", 3)
        [{'title': '...', 'summary': '...', 'source': '...'}]
    """
    params = {
        "q": topic,
        "lang": "en",
        "country": "in",
        "max": count,
        "apikey": api_key,
    }
    response = requests.get(_GNEWS_SEARCH_URL, params=params, timeout=10)
    response.raise_for_status()

    raw_articles = response.json().get("articles", [])
    return [_normalise(a) for a in raw_articles]


def _normalise(article: dict) -> dict:
    """Extract and clean the three fields needed from a raw GNews article dict.

    Args:
        article: A single article object from the GNews API response.
            Expected keys: ``title``, ``description``, ``source`` (nested
            dict with ``name``).

    Returns:
        A flat dict with ``title``, ``summary``, and ``source`` keys.
        ``summary`` falls back to ``title`` when ``description`` is absent
        or empty.  ``source`` falls back to ``"Unknown"`` when the nested
        name is missing.

    Raises:
        Nothing.

    Example:
        >>> raw = {"title": "Foo", "description": "Bar.", "source": {"name": "BBC"}}
        >>> _normalise(raw)
        {'title': 'Foo', 'summary': 'Bar.', 'source': 'BBC'}
    """
    title: str = article.get("title", "").strip()
    description: str = article.get("description", "").strip()
    source_name: str = (article.get("source") or {}).get("name", "Unknown").strip()

    return {
        "title": title,
        "summary": description if description else title,
        "source": source_name,
    }
