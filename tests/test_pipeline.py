"""Smoke tests with mocks (no real API keys)."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import httpx
import pytest
import respx

from market_news.main import run
from market_news.news_client import fetch_news_articles

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>t</title>
<item><title>Real title</title><link>https://news.example/a</link>
<description>&lt;p&gt;Desc&lt;/p&gt;</description></item>
<item><title>[Removed]</title><link>https://x</link></item>
</channel></rss>"""


def _articles_rss(n: int) -> str:
    items = []
    for i in range(n):
        items.append(
            f"<item><title>Headline {i}</title>"
            f"<link>https://example.com/{i}</link>"
            f"<description>Description {i}</description></item>"
        )
    return f"""<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>
    {"".join(items)}</channel></rss>"""


@respx.mock
def test_fetch_news_articles_parses_rss():
    respx.get("https://test.feed/rss.xml").mock(
        return_value=httpx.Response(200, text=SAMPLE_RSS)
    )
    with patch.dict(os.environ, {"RSS_FEEDS": "https://test.feed/rss.xml"}, clear=False):
        out = fetch_news_articles(api_key=None, page_size=10)
    assert len(out) == 1
    assert out[0]["title"] == "Real title"
    assert "Desc" in out[0]["description"]


@respx.mock
def test_fetch_merges_two_feeds_dedupes_by_link():
    xml1 = """<?xml version="1.0"?><rss version="2.0"><channel><title>a</title>
    <item><title>Same</title><link>https://x.com/a</link><description>one</description></item>
    </channel></rss>"""
    xml2 = """<?xml version="1.0"?><rss version="2.0"><channel><title>b</title>
    <item><title>Same</title><link>https://x.com/a</link><description>two</description></item>
    <item><title>Other</title><link>https://x.com/b</link><description>o</description></item>
    </channel></rss>"""
    respx.get("https://one.test/1.xml").mock(return_value=httpx.Response(200, text=xml1))
    respx.get("https://two.test/2.xml").mock(return_value=httpx.Response(200, text=xml2))
    with patch.dict(
        os.environ,
        {"RSS_FEEDS": "https://one.test/1.xml,https://two.test/2.xml"},
        clear=False,
    ):
        out = fetch_news_articles(page_size=10)
    titles = {a["title"] for a in out}
    assert "Other" in titles
    assert len([a for a in out if a["title"] == "Same"]) == 1


@patch.dict(
    os.environ,
    {
        "RSS_FEEDS": "https://news.test/feed.xml",
        "GEMINI_API_KEY": "g",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/FAKE/FAKE/FAKE",
    },
    clear=False,
)
@respx.mock
def test_run_success_posts_digest():
    respx.get("https://news.test/feed.xml").mock(
        return_value=httpx.Response(200, text=_articles_rss(10))
    )
    slack_route = respx.post(
        "https://hooks.slack.com/services/FAKE/FAKE/FAKE"
    ).mock(return_value=httpx.Response(200, text="ok"))

    with patch("market_news.main.run_digest", return_value="**1. X**\n* **Summary:** y"):
        run()

    assert slack_route.called
    sent = slack_route.calls[0].request.content.decode()
    data = json.loads(sent)
    assert "top 5 market-moving" in data["text"].lower()
    assert "**1. X**" in data["text"]


@patch.dict(
    os.environ,
    {
        "RSS_FEEDS": "https://bad.test/feed.xml",
        "GEMINI_API_KEY": "g",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/FAKE/FAKE/FAKE",
    },
    clear=False,
)
@respx.mock
def test_run_failure_sends_fallback():
    respx.get("https://bad.test/feed.xml").mock(
        return_value=httpx.Response(500, text="error")
    )
    slack_route = respx.post(
        "https://hooks.slack.com/services/FAKE/FAKE/FAKE"
    ).mock(return_value=httpx.Response(200, text="ok"))

    run()

    assert slack_route.called
    data = json.loads(slack_route.calls[0].request.content.decode())
    assert "Workflow failed" in data["text"] or "failed" in data["text"].lower()


@patch.dict(
    os.environ,
    {
        "RSS_FEEDS": "https://sparse.test/feed.xml",
        "GEMINI_API_KEY": "g",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/FAKE/FAKE/FAKE",
        "MIN_ARTICLES": "50",
    },
    clear=False,
)
@respx.mock
def test_run_sparse_articles_message():
    respx.get("https://sparse.test/feed.xml").mock(
        return_value=httpx.Response(200, text=_articles_rss(2))
    )
    slack_route = respx.post(
        "https://hooks.slack.com/services/FAKE/FAKE/FAKE"
    ).mock(return_value=httpx.Response(200, text="ok"))

    run()

    assert slack_route.called
    data = json.loads(slack_route.calls[0].request.content.decode())
    assert "No sufficient headlines" in data["text"]


def test_fetch_requires_feed_when_no_urls_configured(monkeypatch):
    import market_news.news_client as nc

    monkeypatch.setattr(nc, "DEFAULT_RSS_FEEDS", ())
    monkeypatch.delenv("RSS_FEEDS", raising=False)
    with pytest.raises(ValueError, match="No RSS"):
        fetch_news_articles()
