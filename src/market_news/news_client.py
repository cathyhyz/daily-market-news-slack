"""Fetch headlines from RSS/Atom feeds (no NewsAPI key)."""

from __future__ import annotations

import html
import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from market_news.rss_parse import parse_feed_xml

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 30.0
MAX_429_RETRIES = 2
BACKOFF_SEC = 2.0

# Default feeds: English-language business / markets (override with RSS_FEEDS).
DEFAULT_RSS_FEEDS: tuple[str, ...] = (
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    # MarketWatch / Dow Jones public feed (301s from legacy marketwatch.com path).
    "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
)

DEFAULT_USER_AGENT = (
    "market-news-digest/1.0 (+https://github.com/readme; automated weekday run)"
)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", text)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def _feed_urls() -> list[str]:
    raw = (os.environ.get("RSS_FEEDS") or "").strip()
    if raw:
        return [u.strip() for u in raw.split(",") if u.strip()]
    return list(DEFAULT_RSS_FEEDS)


def _normalize_link(url: str) -> str:
    if not url:
        return ""
    try:
        p = urlparse(url.strip())
        return f"{p.scheme}://{p.netloc.lower()}{p.path or ''}".rstrip("/")
    except Exception:
        return url.strip().lower()


def _entry_to_article(entry: Any) -> dict | None:
    title = (getattr(entry, "title", None) or "").strip()
    if not title or title == "[Removed]":
        return None
    link = (getattr(entry, "link", None) or "").strip()
    summary = getattr(entry, "summary", None) or getattr(entry, "description", None) or ""
    summary = _strip_html(str(summary))[:2000]
    return {
        "title": title,
        "description": summary,
        "content": "",
        "url": link,
    }


def _published_ts(entry: Any) -> float:
    t = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if t:
        try:
            return float(time.mktime(t))
        except Exception:
            return 0.0
    return 0.0


def _dedupe_entries(entries: list[Any]) -> list[tuple[float, dict]]:
    """Return (timestamp, article) list, one row per dedupe key, newest wins."""
    by_key: dict[str, tuple[float, dict]] = {}
    for entry in entries:
        art = _entry_to_article(entry)
        if not art:
            continue
        key = _normalize_link(art["url"]) or art["title"].lower()
        ts = _published_ts(entry)
        prev = by_key.get(key)
        if prev is None or ts >= prev[0]:
            by_key[key] = (ts, art)
    return list(by_key.values())


def _fetch_feed_xml(client: httpx.Client, url: str, user_agent: str) -> str:
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }
    for attempt in range(MAX_429_RETRIES + 1):
        r = client.get(url, headers=headers)
        if r.status_code == 429 and attempt < MAX_429_RETRIES:
            wait = BACKOFF_SEC * (attempt + 1)
            logger.warning("RSS 429 for %s, retry in %ss", url, wait)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.text
    raise RuntimeError(f"RSS exhausted retries: {url}")


def fetch_news_articles(
    api_key: str | None = None,
    query: str | None = None,
    page_size: int | None = None,
) -> list[dict]:
    """
    Aggregate items from RSS_FEEDS (comma-separated URLs) or built-in defaults.

    ``api_key`` / ``query`` are ignored (kept for call-site compatibility).
    ``page_size`` caps total items after merge (default from NEWS_MAX_ITEMS or 5).
    """
    _ = api_key, query
    max_items = page_size or int((os.environ.get("NEWS_MAX_ITEMS") or "5").strip() or "5")
    max_items = max(3, min(max_items, 100))
    user_agent = (os.environ.get("RSS_USER_AGENT") or "").strip() or DEFAULT_USER_AGENT
    urls = _feed_urls()
    if not urls:
        raise ValueError("No RSS feed URLs configured (RSS_FEEDS empty and no defaults)")

    all_entries: list[Any] = []
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        for url in urls:
            try:
                body = _fetch_feed_xml(client, url, user_agent)
                entries = parse_feed_xml(body)
                logger.info("RSS %s: parsed_entries=%s", url, len(entries))
                all_entries.extend(entries)
            except Exception as e:
                logger.warning("RSS feed failed %s: %s", url, e)

    if not all_entries:
        raise RuntimeError("No articles from any RSS feed (all fetches failed or empty)")

    scored = _dedupe_entries(all_entries)
    scored.sort(key=lambda x: x[0], reverse=True)
    out = [a for _, a in scored[:max_items]]
    logger.info("RSS merged usable=%s (cap=%s)", len(out), max_items)
    return out
