from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from lundin_agent.models import Article


NEWS_URL = "https://www.lundinmining.com/news/"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
}

MONTH_NAME_PATTERN = re.compile(
    r"\b("
    r"January|February|March|April|May|June|"
    r"July|August|September|October|November|December"
    r")\s+\d{1,2},\s+\d{4}\b",
    re.IGNORECASE,
)

ISO_DATE_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b"
)

DATE_FORMATS = (
    "%B %d, %Y",
    "%b %d, %Y",
    "%Y-%m-%d",
    "%d %B %Y",
    "%d %b %Y",
)


def _normalize_text(value: str) -> str:
    """Collapse repeated whitespace and trim the result."""

    return " ".join(value.split())


def _parse_date(value: str) -> date | None:
    """Parse a supported publication-date representation."""

    cleaned_value = _normalize_text(value)

    if not cleaned_value:
        return None

    iso_match = ISO_DATE_PATTERN.search(cleaned_value)

    if iso_match:
        try:
            return datetime.strptime(
                iso_match.group(0),
                "%Y-%m-%d",
            ).date()
        except ValueError:
            pass

    month_match = MONTH_NAME_PATTERN.search(
        cleaned_value
    )

    if month_match:
        candidate = month_match.group(0)

        for date_format in DATE_FORMATS:
            try:
                return datetime.strptime(
                    candidate,
                    date_format,
                ).date()
            except ValueError:
                continue

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(
                cleaned_value,
                date_format,
            ).date()
        except ValueError:
            continue

    return None


def _extract_date_from_element(
    element: Tag,
) -> date | None:
    """
    Extract a publication date from a news entry.

    It checks structured time elements first, then visible text
    around the article link.
    """

    time_element = element.find("time")

    if isinstance(time_element, Tag):
        datetime_attribute = time_element.get(
            "datetime"
        )

        if isinstance(datetime_attribute, str):
            parsed_date = _parse_date(
                datetime_attribute
            )

            if parsed_date is not None:
                return parsed_date

        parsed_date = _parse_date(
            time_element.get_text(
                " ",
                strip=True,
            )
        )

        if parsed_date is not None:
            return parsed_date

    visible_text = element.get_text(
        " ",
        strip=True,
    )

    return _parse_date(visible_text)


def _find_news_container(
    link: Tag,
) -> Tag:
    """
    Find the nearest HTML element likely to represent one news entry.
    """

    candidate_selectors = (
        "article",
        "li",
        ".news-item",
        ".news-list-item",
        ".press-release",
        ".card",
        ".item",
    )

    for selector in candidate_selectors:
        container = link.find_parent(selector)

        if isinstance(container, Tag):
            return container

    parent = link.parent

    if isinstance(parent, Tag):
        return parent

    return link


def _is_valid_news_url(url: str) -> bool:
    """Verify that the URL belongs to Lundin Mining news."""

    parsed_url = urlparse(url)

    hostname = parsed_url.hostname or ""
    path = parsed_url.path.lower().rstrip("/")

    if not hostname.endswith("lundinmining.com"):
        return False

    if path == "/news":
        return False

    return "/news/" in path


def _extract_title(
    link: Tag,
    container: Tag,
) -> str:
    """Extract the announcement title."""

    link_title = _normalize_text(
        link.get_text(
            " ",
            strip=True,
        )
    )

    if len(link_title) >= 10:
        return link_title

    heading = container.find(
        ["h1", "h2", "h3", "h4", "h5"]
    )

    if isinstance(heading, Tag):
        heading_title = _normalize_text(
            heading.get_text(
                " ",
                strip=True,
            )
        )

        if len(heading_title) >= 10:
            return heading_title

    return ""


def fetch_lundin_official(
    max_items: int = 50,
    lookback_days: int = 1,
) -> list[Article]:
    """
    Fetch recent Lundin Mining official announcements.

    Returning an empty list is a normal result when no announcement
    was published during the requested period.
    """

    if max_items < 1:
        raise ValueError(
            "max_items must be greater than zero"
        )

    if lookback_days < 1:
        raise ValueError(
            "lookback_days must be greater than zero"
        )

    response = requests.get(
        NEWS_URL,
        headers=REQUEST_HEADERS,
        timeout=(10, 60),
    )

    response.raise_for_status()

    if not response.text.strip():
        raise RuntimeError(
            "Lundin Mining returned an empty HTML response"
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    today_utc = datetime.now(
        timezone.utc
    ).date()

    earliest_allowed_date = (
        today_utc
        - timedelta(days=lookback_days)
    )

    articles: list[Article] = []
    seen_urls: set[str] = set()

    for link in soup.select("a[href]"):
        if not isinstance(link, Tag):
            continue

        href = link.get("href")

        if not isinstance(href, str):
            continue

        href = href.strip()

        if not href:
            continue

        full_url = urljoin(
            NEWS_URL,
            href,
        )

        if not _is_valid_news_url(full_url):
            continue

        if full_url in seen_urls:
            continue

        container = _find_news_container(link)

        publication_date = _extract_date_from_element(
            container
        )

        if publication_date is None:
            continue

        if publication_date < earliest_allowed_date:
            continue

        if publication_date > today_utc:
            continue

        title = _extract_title(
            link,
            container,
        )

        if not title:
            continue

        seen_urls.add(full_url)

        articles.append(
            Article(
                title=title,
                url=full_url,
                source="Lundin Mining",
                published=publication_date.isoformat(),
                topic=(
                    "Lundin Mining official "
                    "announcements"
                ),
                collector="lundin_official",
            )
        )

        if len(articles) >= max_items:
            break

    articles.sort(
        key=lambda article: article.published,
        reverse=True,
    )

    return articles