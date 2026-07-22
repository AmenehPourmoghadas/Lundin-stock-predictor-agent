from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Allow execution from the repository root:
# python scripts/collect_gdelt.py
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))


from lundin_agent.collectors.gdelt import fetch_gdelt
from lundin_agent.models import Article


LOOKBACK_DAYS = 1
MAX_ITEMS_PER_TOPIC = 50

TOPICS = [
    "Lundin Mining",
    "copper price",
    "Chile copper mining",
]


def article_to_dictionary(
    article: Article,
) -> dict[str, Any]:
    """
    Convert the project's Article dataclass to a dictionary.
    """
    return article.to_dict()


def remove_duplicate_articles(
    articles: list[Article],
) -> list[Article]:
    """
    Remove duplicate articles from the current execution.

    The article URL is used as the unique identifier.
    """
    unique_articles: dict[str, Article] = {}

    for article in articles:
        normalized_url = article.url.strip()

        if not normalized_url:
            continue

        if normalized_url not in unique_articles:
            unique_articles[normalized_url] = article

    return list(unique_articles.values())


def create_output_path(
    collected_at: datetime,
) -> Path:
    """
    Create a timestamped GDELT JSON output path.
    """
    output_directory = REPOSITORY_ROOT / "data"

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = collected_at.strftime("%Y%m%d_%H%M%S")

    return output_directory / f"gdelt_{timestamp}.json"


def main() -> int:
    collected_at = datetime.now(timezone.utc)

    all_articles: list[Article] = []
    errors: list[dict[str, str]] = []
    topic_results: list[dict[str, Any]] = []

    for topic in TOPICS:
        try:
            articles = fetch_gdelt(
                topic=topic,
                max_items=MAX_ITEMS_PER_TOPIC,
                lookback_days=LOOKBACK_DAYS,
            )

            all_articles.extend(articles)

            topic_results.append(
                {
                    "topic": topic,
                    "article_count": len(articles),
                    "status": "success",
                }
            )

            print(
                f"GDELT: collected {len(articles)} "
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

            topic_results.append(
                {
                    "topic": topic,
                    "article_count": 0,
                    "status": "failed",
                    "error": error_message,
                }
            )

            print(
                f"GDELT collection failed for "
                f"'{topic}': {error_message}",
                file=sys.stderr,
            )

    unique_articles = remove_duplicate_articles(
        all_articles
    )

    if not unique_articles:
        if errors:
            print(
                "GDELT collection produced no articles because "
                "one or more requests failed.",
                file=sys.stderr,
            )
            return 1

        print(
            f"No GDELT articles were found during the past "
            f"{LOOKBACK_DAYS} day(s)."
        )
        print("No JSON file was created.")
        return 0

    if errors:
        status = "partial_success"
    else:
        status = "success"

    output_document = {
        "collector": "gdelt",
        "status": status,
        "collected_at_utc": collected_at.isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "max_items_per_topic": MAX_ITEMS_PER_TOPIC,
        "topics": TOPICS,
        "topic_results": topic_results,
        "article_count": len(unique_articles),
        "error_count": len(errors),
        "errors": errors,
        "articles": [
            article_to_dictionary(article)
            for article in unique_articles
        ],
    }

    output_path = create_output_path(collected_at)
    temporary_path = output_path.with_suffix(".json.tmp")

    try:
        with temporary_path.open(
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

        temporary_path.replace(output_path)

    except OSError as error:
        print(
            f"Could not write GDELT JSON file: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        f"Stored {len(unique_articles)} unique "
        f"GDELT article(s) in:"
    )
    print(output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())