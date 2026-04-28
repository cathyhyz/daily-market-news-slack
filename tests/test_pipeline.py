"""Smoke tests with mocks (no real API keys)."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import httpx
import respx

from market_news.main import run
from market_news.news_client import fetch_news_articles


def _articles(n: int) -> list[dict]:
    return [
        {
            "title": f"Headline {i}",
            "description": f"Description {i}",
            "content": "",
            "url": f"https://example.com/{i}",
        }
        for i in range(n)
    ]


@respx.mock
def test_fetch_news_articles_parses_ok():
    payload = {
        "status": "ok",
        "articles": [
            {
                "title": "Real title",
                "description": "Desc",
                "content": None,
                "url": "https://news.example/a",
            },
            {"title": "[Removed]", "description": "", "url": ""},
        ],
    }
    respx.get("https://newsapi.org/v2/everything").mock(
        return_value=httpx.Response(200, json=payload)
    )
    out = fetch_news_articles(api_key="test-key")
    assert len(out) == 1
    assert out[0]["title"] == "Real title"


@patch.dict(
    os.environ,
    {
        "NEWS_API_KEY": "k",
        "GEMINI_API_KEY": "g",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/FAKE/FAKE/FAKE",
    },
    clear=False,
)
@respx.mock
def test_run_success_posts_digest():
    news_json = {"status": "ok", "articles": _articles(10)}
    respx.get("https://newsapi.org/v2/everything").mock(
        return_value=httpx.Response(200, json=news_json)
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
        "NEWS_API_KEY": "k",
        "GEMINI_API_KEY": "g",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/FAKE/FAKE/FAKE",
    },
    clear=False,
)
@respx.mock
def test_run_failure_sends_fallback():
    respx.get("https://newsapi.org/v2/everything").mock(
        return_value=httpx.Response(401, json={"message": "bad key"})
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
        "NEWS_API_KEY": "k",
        "GEMINI_API_KEY": "g",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/FAKE/FAKE/FAKE",
        "MIN_ARTICLES": "50",
    },
    clear=False,
)
@respx.mock
def test_run_sparse_articles_message():
    news_json = {"status": "ok", "articles": _articles(2)}
    respx.get("https://newsapi.org/v2/everything").mock(
        return_value=httpx.Response(200, json=news_json)
    )
    slack_route = respx.post(
        "https://hooks.slack.com/services/FAKE/FAKE/FAKE"
    ).mock(return_value=httpx.Response(200, text="ok"))

    run()

    assert slack_route.called
    data = json.loads(slack_route.calls[0].request.content.decode())
    assert "No sufficient headlines" in data["text"]
