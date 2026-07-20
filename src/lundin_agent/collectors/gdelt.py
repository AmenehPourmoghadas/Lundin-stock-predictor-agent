from __future__ import annotations
import requests
from lundin_agent.models import Article

ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

def fetch_gdelt(topic: str, max_items: int, lookback_hours: int) -> list[Article]:
    params = {
        "query": f'"{topic}"',
        "mode": "artlist",
        "format": "json",
        "maxrecords": min(max_items, 250),
        "timespan": f"{lookback_hours}h",
        "sort": "datedesc",
    }
    response = requests.get(ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    results: list[Article] = []
    for item in payload.get("articles", []):
        results.append(Article(
            title=item.get("title", "").strip(),
            url=item.get("url", ""),
            source=item.get("domain", ""),
            published=item.get("seendate", ""),
            topic=topic,
            collector="gdelt",
        ))
    return results
