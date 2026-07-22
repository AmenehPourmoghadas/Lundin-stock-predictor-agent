from __future__ import annotations

import json
from pathlib import Path

from lundin_agent.models import Article


HISTORY_FILE = Path("data/article_history.json")


def load_history() -> list[Article]:
    """
    Load article history from disk.
    Returns an empty list if the file does not exist.
    """

    if not HISTORY_FILE.exists():
        return []

    with HISTORY_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return [Article(**item) for item in data]


def save_history(articles: list[Article]) -> None:
    """
    Save article history to disk.
    """

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    with HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            [article.model_dump() for article in articles],
            f,
            indent=2,
            ensure_ascii=False,
        )


def merge_history(
    existing: list[Article],
    new: list[Article],
) -> list[Article]:
    """
    Merge articles while removing duplicates.
    URL is treated as the unique key.
    """

    merged: dict[str, Article] = {}

    for article in existing + new:
        merged[article.url] = article

    articles = list(merged.values())

    articles.sort(
        key=lambda article: article.published,
        reverse=True,
    )

    return articles
