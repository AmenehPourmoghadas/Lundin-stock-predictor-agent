from __future__ import annotations

import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


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

# Request protection settings
MAX_ATTEMPTS_PER_TOPIC = 3
INITIAL_BACKOFF_SECONDS = 45
MINIMUM_TOPIC_DELAY_SECONDS = 30
MAXIMUM_TOPIC_DELAY_SECONDS = 45

RETRYABLE_HTTP_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


def article_to_dictionary(
    article: Article,
) -> dict[str, Any]:
    """
    Convert the project's Article dataclass into a dictionary.
    """
    return article.to_dict()


def remove_duplicate_articles(
    articles: list[Article],
) -> list[Article]:
    """
    Remove duplicate articles using the article URL.
    """
    unique_articles: dict[str, Article] = {}

    for article in articles:
        normalized_url = (article.url or "").strip()

        if not normalized_url:
            continue

        if normalized_url not in unique_articles:
            unique_articles[normalized_url] = article

    return list(unique_articles.values())


def create_output_path(
    collected_at: datetime,
) -> Path:
    """
    Create the timestamped GDELT output path.
    """
    output_directory = REPOSITORY_ROOT / "data"

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = collected_at.strftime("%Y%m%d_%H%M%S")

    return output_directory / f"gdelt_{timestamp}.json"


def get_http_status_code(
    error: Exception,
) -> int | None:
    """
    Extract an HTTP status code from a requests exception when available.
    """
    response = getattr(error, "response", None)

    if response is None:
        return None

    return getattr(response, "status_code", None)


def get_retry_after_seconds(
    error: Exception,
) -> int | None:
    """
    Read a numeric Retry-After header when GDELT provides one.
    """
    response = getattr(error, "response", None)

    if response is None:
        return None

    retry_after = response.headers.get("Retry-After")

    if retry_after and retry_after.isdigit():
        return int(retry_after)

    return None


def is_retryable_error(
    error: Exception,
) -> bool:
    """
    Decide whether a request should be attempted again.
    """
    status_code = get_http_status_code(error)

    if status_code in RETRYABLE_HTTP_STATUS_CODES:
        return True

    if isinstance(
        error,
        (
            requests.Timeout,
            requests.ConnectionError,
        ),
    ):
        return True

    return False


def calculate_wait_seconds(
    error: Exception,
    attempt_number: int,
) -> float:
    """
    Calculate Retry-After or exponential-backoff delay with jitter.
    """
    retry_after = get_retry_after_seconds(error)

    if retry_after is not None:
        return float(retry_after) + random.uniform(1, 5)

    exponential_delay = (
        INITIAL_BACKOFF_SECONDS
        * (2 ** (attempt_number - 1))
    )

    jitter = random.uniform(5, 15)

    return exponential_delay + jitter


def fetch_topic_with_retry(
    topic: str,
) -> list[Article]:
    """
    Fetch one GDELT topic with conservative retry handling.
    """
    last_error: Exception | None = None

    for attempt_number in range(
        1,
        MAX_ATTEMPTS_PER_TOPIC + 1,
    ):
        try:
            print(
                f"GDELT: requesting '{topic}' "
                f"(attempt {attempt_number}/"
                f"{MAX_ATTEMPTS_PER_TOPIC})."
            )

            return fetch_gdelt(
                topic=topic,
                max_items=MAX_ITEMS_PER_TOPIC,
                lookback_days=LOOKBACK_DAYS,
            )

        except Exception as error:
            last_error = error
            status_code = get_http_status_code(error)

            print(
                f"GDELT request failed for '{topic}': "
                f"{type(error).__name__}: {error}",
                file=sys.stderr,
            )

            if not is_retryable_error(error):
                raise

            if attempt_number >= MAX_ATTEMPTS_PER_TOPIC:
                break

            wait_seconds = calculate_wait_seconds(
                error=error,
                attempt_number=attempt_number,
            )

            if status_code == 429:
                reason = "rate limited"
            else:
                reason = "temporary endpoint failure"

            print(
                f"GDELT is {reason}. Waiting "
                f"{wait_seconds:.1f} seconds before retrying.",
                file=sys.stderr,
            )

            time.sleep(wait_seconds)

    raise RuntimeError(
        f"GDELT failed for '{topic}' after "
        f"{MAX_ATTEMPTS_PER_TOPIC} attempts. "
        f"Last error: {last_error}"
    )


def main() -> int:
    collected_at = datetime.now(timezone.utc)

    all_articles: list[Article] = []
    errors: list[dict[str, str]] = []
    topic_results: list[dict[str, Any]] = []

    for topic_index, topic in enumerate(TOPICS):
        try:
            articles = fetch_topic_with_retry(topic)

            all_articles.extend(articles)

            topic_results.append(
                {
                    "topic": topic,
                    "status": "success",
                    "article_count": len(articles),
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
                    "status": "failed",
                    "article_count": 0,
                    "error": error_message,
                }
            )

            print(
                f"GDELT collection ultimately failed for "
                f"'{topic}': {error_message}",
                file=sys.stderr,
            )

        # Avoid immediately sending the next topic request.
        if topic_index < len(TOPICS) - 1:
            delay_seconds = random.uniform(
                MINIMUM_TOPIC_DELAY_SECONDS,
                MAXIMUM_TOPIC_DELAY_SECONDS,
            )

            print(
                f"Waiting {delay_seconds:.1f} seconds "
                "before the next GDELT topic."
            )

            time.sleep(delay_seconds)

    # All-or-nothing behavior:
    # Never write an incomplete GDELT file when any topic failed.
    if errors:
        print(
            f"GDELT collector failed for {len(errors)} of "
            f"{len(TOPICS)} topic(s).",
            file=sys.stderr,
        )
        print(
            "No GDELT JSON file was created because the "
            "collection was incomplete.",
            file=sys.stderr,
        )
        return 1

    unique_articles = remove_duplicate_articles(
        all_articles
    )

    if not unique_articles:
        print(
            f"No GDELT articles were found during the past "
            f"{LOOKBACK_DAYS} day(s)."
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
        temporary_path.unlink(missing_ok=True)

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