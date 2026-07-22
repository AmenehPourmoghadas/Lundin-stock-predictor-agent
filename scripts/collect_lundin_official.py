from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))


from lundin_agent.collectors.lundin_official import (
    fetch_lundin_official,
)
from lundin_agent.models import Article


LOOKBACK_DAYS = 1
MAX_ITEMS = 50

ARTICLE_TIMEOUT_SECONDS = 12
MAX_SUMMARY_SENTENCES = 3
MAX_SUMMARY_CHARACTERS = 900
MIN_PARAGRAPH_CHARACTERS = 80

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; "
        "LundinStockResearchAgent/1.0; "
        "+https://github.com/AmenehPourmoghadas/"
        "Lundin-stock-predictor-agent)"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def truncate_text(value: str, maximum_characters: int) -> str:
    if len(value) <= maximum_characters:
        return value

    shortened = value[:maximum_characters].rsplit(" ", 1)[0]

    return f"{shortened}..."


def create_summary_from_text(text: str) -> str:
    cleaned_text = normalize_text(text)

    if not cleaned_text:
        return ""

    sentences = re.split(
        r"(?<=[.!?])\s+(?=[A-Z0-9\"'])",
        cleaned_text,
    )

    selected_sentences: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence = normalize_text(sentence)

        if len(sentence) < 25:
            continue

        projected_length = current_length + len(sentence)

        if selected_sentences:
            projected_length += 1

        if projected_length > MAX_SUMMARY_CHARACTERS:
            break

        selected_sentences.append(sentence)
        current_length = projected_length

        if len(selected_sentences) >= MAX_SUMMARY_SENTENCES:
            break

    if selected_sentences:
        return truncate_text(
            " ".join(selected_sentences),
            MAX_SUMMARY_CHARACTERS,
        )

    return truncate_text(
        cleaned_text,
        MAX_SUMMARY_CHARACTERS,
    )


def extract_page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for element in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
            "form",
            "aside",
        ]
    ):
        element.decompose()

    description_selectors = [
        ("meta", {"name": "description"}),
        ("meta", {"property": "og:description"}),
        ("meta", {"name": "twitter:description"}),
    ]

    for tag_name, attributes in description_selectors:
        tag = soup.find(tag_name, attrs=attributes)

        if tag:
            description = normalize_text(
                str(tag.get("content", ""))
            )

            if len(description) >= MIN_PARAGRAPH_CHARACTERS:
                return description

    article_container = (
        soup.find("article")
        or soup.find("main")
        or soup.body
    )

    if article_container is None:
        return ""

    paragraphs: list[str] = []

    for paragraph in article_container.find_all("p"):
        paragraph_text = normalize_text(
            paragraph.get_text(" ", strip=True)
        )

        if len(paragraph_text) < MIN_PARAGRAPH_CHARACTERS:
            continue

        paragraphs.append(paragraph_text)

        if len(" ".join(paragraphs)) >= 3000:
            break

    return " ".join(paragraphs)


def fetch_article_summary(url: str) -> str:
    normalized_url = url.strip()

    if not normalized_url:
        return ""

    parsed_url = urlparse(normalized_url)

    if parsed_url.scheme not in {"http", "https"}:
        return ""

    try:
        response = requests.get(
            normalized_url,
            headers=REQUEST_HEADERS,
            timeout=ARTICLE_TIMEOUT_SECONDS,
            allow_redirects=True,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        if (
            "text/html" not in content_type
            and "application/xhtml+xml" not in content_type
        ):
            return ""

        page_text = extract_page_text(response.text)

        return create_summary_from_text(page_text)

    except (
        requests.RequestException,
        ValueError,
        UnicodeError,
    ):
        return ""


def article_to_dictionary(
    article: Article,
) -> dict[str, Any]:
    article_payload = article.to_dict()

    article_payload["summary"] = fetch_article_summary(
        article.url
    )

    return article_payload


def remove_duplicate_articles(
    articles: list[Article],
) -> list[Article]:
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
    output_directory = REPOSITORY_ROOT / "data"

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = collected_at.strftime("%Y%m%d_%H%M%S")

    return (
        output_directory
        / f"lundin_official_{timestamp}.json"
    )


def write_articles(
    articles: list[Article],
    collected_at: datetime,
) -> tuple[Path, int]:
    output_path = create_output_path(collected_at)

    article_payloads: list[dict[str, Any]] = []

    for index, article in enumerate(
        articles,
        start=1,
    ):
        print(
            f"Lundin Official: enriching announcement "
            f"{index}/{len(articles)}."
        )

        article_payloads.append(
            article_to_dictionary(article)
        )

    summaries_created = sum(
        1
        for article_payload in article_payloads
        if article_payload["summary"]
    )

    output_document = {
        "collector": "lundin_official",
        "status": "success",
        "collected_at_utc": collected_at.isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "article_count": len(articles),
        "summary_count": summaries_created,
        "articles": article_payloads,
    }

    temporary_path = output_path.with_suffix(
        ".json.tmp"
    )

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

    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise

    return output_path, summaries_created


def main() -> int:
    collected_at = datetime.now(timezone.utc)

    try:
        articles = fetch_lundin_official(
            max_items=MAX_ITEMS,
            lookback_days=LOOKBACK_DAYS,
        )

    except requests.RequestException as error:
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
        print("No JSON file was created.")

        return 0

    try:
        output_path, summaries_created = write_articles(
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
        f"Summaries created: {summaries_created}/"
        f"{len(unique_articles)}."
    )
    print(f"Created: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
