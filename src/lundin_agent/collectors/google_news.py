from __future__ import annotations
import urllib.parse
import feedparser
from lundin_agent.models import Article

def fetch_google_news(topic: str, max_items: int) -> list[Article]:
    query = urllib.parse.quote(f"{topic} when:1d")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    results: list[Article] = []
    for entry in feed.entries[:max_items]:
        source = entry.get("source", {})
        results.append(Article(
            title=entry.get("title", "").strip(),
            url=entry.get("link", ""),
            source=source.get("title", "") if isinstance(source, dict) else "",
            published=entry.get("published", ""),
            topic=topic,
            collector="google_news",
        ))
    return results
