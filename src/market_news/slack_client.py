"""Post messages to Slack via Incoming Webhook."""

from __future__ import annotations

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 30.0


def post_slack_text(text: str, webhook_url: str | None = None) -> None:
    """POST JSON {\"text\": ...} to Slack Incoming Webhook."""
    url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        raise ValueError("SLACK_WEBHOOK_URL is not set")

    payload = {"text": text}
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        r = client.post(
            url,
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        # Slack returns "ok" in body for webhooks
        body = (r.text or "").strip()
        if body and body != "ok":
            logger.debug("Slack webhook response: %s", body[:200])


def format_digest_for_slack(llm_body: str) -> str:
    """Prefix intro line; body is already structured mrkdwn-friendly from the model."""
    intro = "Good morning! \u2615 Here are the top 5 market-moving stories for today:\n\n"
    return intro + llm_body
