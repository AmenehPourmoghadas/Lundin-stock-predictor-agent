from __future__ import annotations
import re
from difflib import SequenceMatcher
from lundin_agent.models import Article

def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", title.lower()).strip()

def deduplicate(articles: list[Article], threshold: float = 0.88) -> list[Article]:
    kept: list[Article] = []
    normalized: list[str] = []
    for article in articles:
        candidate = normalize_title(article.title)
        if not candidate:
            continue
        if any(SequenceMatcher(None, candidate, existing).ratio() >= threshold for existing in normalized):
            continue
        kept.append(article)
        normalized.append(candidate)
    return kept
