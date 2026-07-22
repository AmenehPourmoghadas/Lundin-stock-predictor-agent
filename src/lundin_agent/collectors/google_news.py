from __future__ import annotations

import urllib.parse

import feedparser
import requests

from lundin_agent.models import Article


GOOGLE_NEWS_RSS_ENDPOINT = "https://news.google.com/rss/search"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/xml, text/xml, "
        "text/html;q=0.9, */*;q=0.8"
    ),
}


def fetch_google_news(
    topic: str,
    max_items: int = 50,
    lookback_days: int = 1,
) -> list[Article]:
    """
    Fetch Google News RSS articles for a topic.

    The default lookback period is one day.
    This function only collects and returns articles.
    It does not write files.
    """

    topic = topic.strip()

    if not topic:
        raise ValueError("topic must not be empty")

    if max_items < 1:
        raise ValueError("max_items must be greater than zero")

    if lookback_days < 1:
        raise ValueError("lookback_days must be greater than zero")

    query = urllib.parse.quote(
        f"{topic} when:{lookback_days}d"
    )

    url = (
        f"{GOOGLE_NEWS_RSS_ENDPOINT}"
        f"?q={query}"
        f"&hl=en-US"
        f"&gl=US"
        f"&ceid=US:en"
    )

    response = requests.get(
        url,
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        raise RuntimeError(
            f"Google News RSS parsing failed for topic '{topic}': "
            f"{feed.bozo_exception}"
        )

    articles: list[Article] = []

    for entry in feed.entries[:max_items]:
        title = entry.get("title", "").strip()
        article_url = entry.get("link", "").strip()

        if not title or not article_url:
            continue

        source_data = entry.get("source", {})

        if isinstance(source_data, dict):
            source_name = source_data.get("title", "").strip()
        else:
            source_name = ""

        articles.append(
            Article(
                title=title,
                url=article_url,
                source=source_name,
                published=entry.get("published", "").strip(),
                topic=topic,
                collector="google_news",
            )
        )

    return articles