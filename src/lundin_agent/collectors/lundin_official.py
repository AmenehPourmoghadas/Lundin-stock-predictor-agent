from __future__ import annotations
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from lundin_agent.models import Article

NEWS_URL = "https://www.lundinmining.com/news/"

def fetch_lundin_official(max_items: int = 15) -> list[Article]:
    response = requests.get(
        NEWS_URL,
        timeout=30,
        headers={"User-Agent": "lundin-agent/0.1 (+https://github.com/AmenehPourmoghadas/lundin-agent)"},
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results: list[Article] = []
    seen: set[str] = set()

    for link in soup.select("a[href]"):
        title = " ".join(link.get_text(" ", strip=True).split())
        href = link.get("href", "")
        if not title or len(title) < 20:
            continue
        full_url = urljoin(NEWS_URL, href)
        if "news" not in full_url.lower() or full_url in seen:
            continue
        seen.add(full_url)
        results.append(Article(
            title=title,
            url=full_url,
            source="Lundin Mining",
            published="",
            topic="Lundin Mining official announcements",
            collector="lundin_official",
        ))
        if len(results) >= max_items:
            break
    return results
