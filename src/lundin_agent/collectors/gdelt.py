from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from lundin_agent.models import Article


GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def fetch_gdelt(
    topic: str,
    max_items: int = 50,
    lookback_days: int = 1,
) -> list[Article]:
    """
    Fetch GDELT articles published during the configured lookback period.

    This function only fetches and returns Article objects.
    It does not write files.
    """

    topic = topic.strip()

    if not topic:
        raise ValueError("topic must not be empty")

    if max_items < 1:
        raise ValueError("max_items must be greater than zero")

    if lookback_days < 1:
        raise ValueError("lookback_days must be greater than zero")

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=lookback_days)

    params = {
        "query": topic,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": min(max_items, 250),
        "sort": "DateDesc",
        "startdatetime": start_time.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end_time.strftime("%Y%m%d%H%M%S"),
    }

    response = requests.get(
        GDELT_ENDPOINT,
        params=params,
        headers=REQUEST_HEADERS,
        timeout=60,
    )

    response.raise_for_status()

    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise RuntimeError(
            "GDELT returned a response that was not valid JSON"
        ) from error

    raw_articles = payload.get("articles", [])

    if not isinstance(raw_articles, list):
        raise RuntimeError(
            "GDELT response field 'articles' was not a list"
        )

    articles: list[Article] = []

    for item in raw_articles[:max_items]:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "")).strip()
        article_url = str(item.get("url", "")).strip()

        if not title or not article_url:
            continue

        source = str(
            item.get("domain")
            or item.get("sourcecountry")
            or ""
        ).strip()

        published = str(
            item.get("seendate")
            or item.get("date")
            or ""
        ).strip()

        articles.append(
            Article(
                title=title,
                url=article_url,
                source=source,
                published=published,
                topic=topic,
                collector="gdelt",
            )
        )

    return articles
