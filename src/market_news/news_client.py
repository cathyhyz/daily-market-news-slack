"""Fetch headlines via NewsAPI.org (everything endpoint, last 24h)."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

NEWSAPI_EVERYTHING = "https://newsapi.org/v2/everything"
DEFAULT_QUERY = "(stock market OR S&P 500 OR Federal Reserve OR earnings OR inflation OR treasury)"
DEFAULT_PAGE_SIZE = 30
HTTP_TIMEOUT = 30.0
MAX_429_RETRIES = 2
BACKOFF_SEC = 2.0


def _from_iso_utc() -> str:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return since.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_news_articles(
    api_key: str | None = None,
    query: str | None = None,
    page_size: int | None = None,
) -> list[dict]:
    """
    Return list of article dicts (title, description, content, url) from NewsAPI.
    Retries on HTTP 429 with backoff.
    """
    key = api_key or os.environ.get("NEWS_API_KEY")
    if not key:
        raise ValueError("NEWS_API_KEY is not set")

    q = query or os.environ.get("NEWS_QUERY", DEFAULT_QUERY)
    size = page_size or int(os.environ.get("NEWS_PAGE_SIZE", str(DEFAULT_PAGE_SIZE)))
    size = max(1, min(size, 100))

    params = {
        "q": q,
        "language": "en",
        "sortBy": "publishedAt",
        "from": _from_iso_utc(),
        "pageSize": size,
        "page": 1,
    }
    headers = {"X-Api-Key": key}

    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        for attempt in range(MAX_429_RETRIES + 1):
            r = client.get(NEWSAPI_EVERYTHING, params=params, headers=headers)
            if r.status_code == 429:
                if attempt < MAX_429_RETRIES:
                    wait = BACKOFF_SEC * (attempt + 1)
                    logger.warning("NewsAPI 429, retrying in %s s", wait)
                    time.sleep(wait)
                    continue
            r.raise_for_status()
            data = r.json()
            if data.get("status") != "ok":
                raise RuntimeError(data.get("message") or "NewsAPI returned non-ok status")
            articles = data.get("articles") or []
            out: list[dict] = []
            for a in articles:
                if not isinstance(a, dict):
                    continue
                title = a.get("title")
                if not title or title == "[Removed]":
                    continue
                out.append(
                    {
                        "title": title,
                        "description": a.get("description") or "",
                        "content": (a.get("content") or "")[:500],
                        "url": a.get("url") or "",
                    }
                )
            return out

    raise RuntimeError("NewsAPI request exhausted retries without success")
