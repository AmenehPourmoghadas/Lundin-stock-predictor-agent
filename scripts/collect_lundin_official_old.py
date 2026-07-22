from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(
    __file__
).resolve().parents[1]

SOURCE_DIRECTORY = (
    REPOSITORY_ROOT / "src"
)

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


from lundin_agent.collectors.lundin_official import (
    fetch_lundin_official,
)
from lundin_agent.models import Article


LOOKBACK_DAYS = 1
MAX_ITEMS = 50


def remove_duplicate_articles(
    articles: list[Article],
) -> list[Article]:
    """
    Remove duplicate announcements based on URL.
    """

    unique_articles: dict[str, Article] = {}

    for article in articles:
        normalized_url = article.url.strip()

        if not normalized_url:
            continue

        if normalized_url not in unique_articles:
            unique_articles[
                normalized_url
            ] = article

    return list(
        unique_articles.values()
    )


def create_output_path(
    collected_at: datetime,
) -> Path:
    """
    Create a timestamped output path under data/.
    """

    output_directory = (
        REPOSITORY_ROOT / "data"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = collected_at.strftime(
        "%Y%m%d_%H%M%S"
    )

    return (
        output_directory
        / f"lundin_official_{timestamp}.json"
    )


def write_articles(
    articles: list[Article],
    collected_at: datetime,
) -> Path:
    """
    Write collected announcements to a timestamped JSON file.
    """

    output_path = create_output_path(
        collected_at
    )

    output_document = {
        "collector": "lundin_official",
        "status": "success",
        "collected_at_utc": (
            collected_at.isoformat()
        ),
        "lookback_days": LOOKBACK_DAYS,
        "article_count": len(articles),
        "articles": [
            article.to_dict()
            for article in articles
        ],
    }

    temporary_path = output_path.with_suffix(
        ".json.tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            output_document,
            output_file,
            indent=2,
            ensure_ascii=False,
        )

    temporary_path.replace(
        output_path
    )

    return output_path


def main() -> int:
    collected_at = datetime.now(
        timezone.utc
    )

    try:
        articles = fetch_lundin_official(
            max_items=MAX_ITEMS,
            lookback_days=LOOKBACK_DAYS,
        )
    except requests.exceptions.RequestException as error:
        print(
            "Lundin official website request failed: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1
    except Exception as error:
        print(
            "Lundin official collection failed: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1

    unique_articles = remove_duplicate_articles(
        articles
    )

    if not unique_articles:
        print(
            "No Lundin Mining official announcements "
            f"were published during the past "
            f"{LOOKBACK_DAYS} day(s)."
        )
        print(
            "No JSON file was created."
        )
        return 0

    try:
        output_path = write_articles(
            articles=unique_articles,
            collected_at=collected_at,
        )
    except OSError as error:
        print(
            "Could not write the Lundin official "
            f"JSON file: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        f"Collected {len(unique_articles)} "
        "Lundin official announcement(s)."
    )
    print(
        f"Created: {output_path}"
    )

    return 0


if __name__ == "__main__":
    import requests

    raise SystemExit(main())
