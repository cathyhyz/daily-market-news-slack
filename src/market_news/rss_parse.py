"""Minimal RSS 2.0 / Atom feed parsing (stdlib only)."""

from __future__ import annotations

import email.utils
import logging
import time
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from typing import Any

logger = logging.getLogger(__name__)


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def _find_children(parent: ET.Element, name: str) -> list[ET.Element]:
    n = name.lower()
    return [c for c in list(parent) if _local(c.tag).lower() == n]


def _item_description(item: ET.Element) -> str:
    for c in list(item):
        ln = _local(c.tag).lower()
        if ln == "description":
            return _text(c)
    for c in list(item):
        ln = _local(c.tag).lower()
        if "encoded" in ln:
            return _text(c)
    return ""


def _parse_pub_struct(raw: str) -> Any:
    if not raw:
        return None
    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(raw).timetuple()
    except Exception:
        pass
    try:
        t = email.utils.parsedate_tz(raw)
        if t and t[0]:
            return time.gmtime(email.utils.mktime_tz(t))
    except Exception:
        pass
    return None


def _parse_rss_channel(channel: ET.Element) -> list[SimpleNamespace]:
    out: list[SimpleNamespace] = []
    for item in _find_children(channel, "item"):
        titles = _find_children(item, "title")
        links = _find_children(item, "link")
        title = _text(titles[0]) if titles else ""
        link = _text(links[0]) if links else ""
        summary = _item_description(item)
        pub = None
        for tag in ("pubDate", "published", "updated"):
            pk = _find_children(item, tag)
            if pk:
                pub = _parse_pub_struct(_text(pk[0]))
                break
        out.append(
            SimpleNamespace(
                title=title,
                link=link,
                summary=summary,
                description=summary,
                published_parsed=pub,
                updated_parsed=pub,
            )
        )
    return out


def _atom_link(entry: ET.Element) -> str:
    for link in _find_children(entry, "link"):
        href = (link.get("href") or "").strip()
        rel = (link.get("rel") or "alternate").lower()
        if href and rel in ("alternate", ""):
            return href
    for link in _find_children(entry, "link"):
        href = (link.get("href") or "").strip()
        if href:
            return href
    return ""


def _parse_atom_feed(feed: ET.Element) -> list[SimpleNamespace]:
    out: list[SimpleNamespace] = []
    for entry in _find_children(feed, "entry"):
        titles = _find_children(entry, "title")
        title = _text(titles[0]) if titles else ""
        link = _atom_link(entry)
        summary = ""
        for tag in ("summary", "content"):
            kids = _find_children(entry, tag)
            if kids:
                summary = _text(kids[0])
                break
        pub = None
        for tag in ("published", "updated"):
            pk = _find_children(entry, tag)
            if pk:
                raw = _text(pk[0])
                if raw:
                    try:
                        from datetime import datetime

                        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                        pub = dt.utctimetuple()
                    except Exception:
                        pass
                break
        out.append(
            SimpleNamespace(
                title=title,
                link=link,
                summary=summary,
                description=summary,
                published_parsed=pub,
                updated_parsed=pub,
            )
        )
    return out


def parse_feed_xml(body: str) -> list[Any]:
    """Return entry-like objects (title, link, summary, published_parsed)."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        logger.warning("XML parse error: %s", e)
        return []

    tag = _local(root.tag).lower()
    if tag == "rss":
        channels = _find_children(root, "channel")
        if not channels:
            return []
        merged: list[SimpleNamespace] = []
        for ch in channels:
            merged.extend(_parse_rss_channel(ch))
        return merged
    if tag == "feed":
        return _parse_atom_feed(root)

    logger.warning("Unknown feed root element: %s", root.tag)
    return []
