from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Allow execution from the repository root:
# python scripts/collect_google_news.py
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))


from lundin_agent.collectors.google_news import fetch_google_news
from lundin_agent.models import Article


LOOKBACK_DAYS = 1
MAX_ITEMS_PER_TOPIC = 50

TOPICS = [
    "Lundin Mining",
    "copper price",
    "Chile copper mining",
]


def article_to_dictionary(article: Article) -> dict[str, Any]:
    """
    Convert an Article model to a JSON-compatible dictionary.

    Supports both Pydantic v2 and Pydantic v1.
    """

    if hasattr(article, "model_dump"):
        return article.model_dump()

    if hasattr(article, "dict"):
        return article.dict()

    raise TypeError(
        "Article must provide model_dump() or dict()"
    )


def remove_duplicate_articles(
    articles: list[Article],
) -> list[Article]:
    """
    Remove duplicate articles from the current execution.

    The article URL is used as the primary unique identifier.
    """

    unique_articles: dict[str, Article] = {}

    for article in articles:
        url = article.url.strip()

        if not url:
            continue

        if url not in unique_articles:
            unique_articles[url] = article

    return list(unique_articles.values())


def create_output_path(
    collected_at: datetime,
) -> Path:
    """
    Create a timestamped Google News output path.
    """

    output_directory = REPOSITORY_ROOT / "data"
    output_directory.mkdir(parents=True, exist_ok=True)

    timestamp = collected_at.strftime("%Y%m%d_%H%M%S")

    return output_directory / f"google_news_{timestamp}.json"


def main() -> int:
    collected_at = datetime.now(timezone.utc)

    all_articles: list[Article] = []
    errors: list[dict[str, str]] = []

    for topic in TOPICS:
        try:
            articles = fetch_google_news(
                topic=topic,
                max_items=MAX_ITEMS_PER_TOPIC,
                lookback_days=LOOKBACK_DAYS,
            )

            all_articles.extend(articles)

            print(
                f"Google News: collected {len(articles)} "
                f"article(s) for '{topic}'."
            )

        except Exception as error:
            error_message = (
                f"{type(error).__name__}: {error}"
            )

            errors.append(
                {
                    "topic": topic,
                    "error": error_message,
                }
            )

            print(
                f"Google News collection failed for "
                f"'{topic}': {error_message}"
            )

    unique_articles = remove_duplicate_articles(
        all_articles
    )

    output_path = create_output_path(collected_at)

    if unique_articles and not errors:
        status = "success"
    elif unique_articles and errors:
        status = "partial_success"
    else:
        status = "failed"

    output_document = {
        "collector": "google_news",
        "status": status,
        "collected_at_utc": collected_at.isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "max_items_per_topic": MAX_ITEMS_PER_TOPIC,
        "topics": TOPICS,
        "article_count": len(unique_articles),
        "error_count": len(errors),
        "errors": errors,
        "articles": [
            article_to_dictionary(article)
            for article in unique_articles
        ],
    }

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            output_document,
            output_file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    print(
        f"Stored {len(unique_articles)} unique article(s) in:"
    )
    print(output_path)

    # Return failure only when no article was collected.
    # The JSON file is still written with the error details.
    return 0 if unique_articles else 1


if __name__ == "__main__":
    raise SystemExit(main())
