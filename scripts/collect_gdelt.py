from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))


from lundin_agent.collectors.gdelt import fetch_gdelt
from lundin_agent.models import Article


LOOKBACK_DAYS = 1
MAX_ITEMS_PER_TOPIC = 50
RETRY_DELAY_SECONDS = 30

TOPICS = [
    "Lundin Mining",
    "copper price",
    "Chile copper mining",
]

RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


def article_to_dict(article: Article) -> dict[str, Any]:
    return article.to_dict()


def get_status_code(error: Exception) -> int | None:
    response = getattr(error, "response", None)

    if response is None:
        return None

    return getattr(response, "status_code", None)


def is_retryable_error(error: Exception) -> bool:
    status_code = get_status_code(error)

    if status_code in RETRYABLE_STATUS_CODES:
        return True

    return isinstance(
        error,
        (
            requests.Timeout,
            requests.ConnectionError,
        ),
    )


def fetch_topic(topic: str) -> list[Article]:
    """
    Request one GDELT topic.

    Attempt 1:
        Run immediately.

    Retry:
        Only for HTTP 429, selected 5xx errors, timeout,
        or connection failure.

    Attempt 2:
        Run once after a 30-second delay.

    After the second failure:
        Raise the error immediately. There is no third attempt.
    """

    try:
        print(f"GDELT: requesting '{topic}' (attempt 1/2).")

        return fetch_gdelt(
            topic=topic,
            max_items=MAX_ITEMS_PER_TOPIC,
            lookback_days=LOOKBACK_DAYS,
        )

    except Exception as first_error:
        if not is_retryable_error(first_error):
            raise

        print(
            f"GDELT temporary failure for '{topic}': "
            f"{type(first_error).__name__}: {first_error}",
            file=sys.stderr,
        )

        print(
            f"Waiting {RETRY_DELAY_SECONDS} seconds, "
            "then retrying exactly once.",
            file=sys.stderr,
        )

        time.sleep(RETRY_DELAY_SECONDS)

    print(f"GDELT: requesting '{topic}' (attempt 2/2).")

    # Any error from the second attempt is propagated immediately.
    # There is no additional retry.
    return fetch_gdelt(
        topic=topic,
        max_items=MAX_ITEMS_PER_TOPIC,
        lookback_days=LOOKBACK_DAYS,
    )


def remove_duplicates(
    articles: list[Article],
) -> list[Article]:
    unique_articles: dict[str, Article] = {}

    for article in articles:
        url = (article.url or "").strip()

        if not url:
            continue

        if url not in unique_articles:
            unique_articles[url] = article

    return list(unique_articles.values())


def create_output_path(
    collected_at: datetime,
) -> Path:
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
    topic_results: list[dict[str, Any]] = []

    for topic in TOPICS:
        try:
            articles = fetch_topic(topic)

        except Exception as error:
            print(
                f"GDELT collection failed for '{topic}': "
                f"{type(error).__name__}: {error}",
                file=sys.stderr,
            )

            print(
                "No GDELT JSON file was created.",
                file=sys.stderr,
            )

            return 1

        all_articles.extend(articles)

        topic_results.append(
            {
                "topic": topic,
                "status": "success",
                "article_count": len(articles),
            }
        )

        print(
            f"GDELT: collected {len(articles)} article(s) "
            f"for '{topic}'."
        )

    unique_articles = remove_duplicates(all_articles)

    if not unique_articles:
        print(
            "GDELT completed successfully but returned no articles."
        )
        print("No GDELT JSON file was created.")

        return 0

    output_document = {
        "collector": "gdelt",
        "status": "success",
        "collected_at_utc": collected_at.isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "max_items_per_topic": MAX_ITEMS_PER_TOPIC,
        "topics": TOPICS,
        "topic_results": topic_results,
        "article_count": len(unique_articles),
        "articles": [
            article_to_dict(article)
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
        temporary_path.unlink(missing_ok=True)

        print(
            f"Failed to write GDELT JSON file: {error}",
            file=sys.stderr,
        )

        return 1

    print(
        f"Created GDELT file with "
        f"{len(unique_articles)} unique article(s):"
    )
    print(output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())