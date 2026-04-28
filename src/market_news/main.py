"""Orchestrator: news -> LLM -> Slack with error fallback."""

from __future__ import annotations

import logging
import os

from market_news.llm_client import run_digest
from market_news.news_client import fetch_news_articles
from market_news.slack_client import format_digest_for_slack, post_slack_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MIN_ARTICLES = int(os.environ.get("MIN_ARTICLES", "3"))


def _safe_error_message(exc: BaseException) -> str:
    msg = str(exc).strip() or exc.__class__.__name__
    if len(msg) > 400:
        msg = msg[:397] + "..."
    return msg


def run() -> None:
    webhook = os.environ.get("SLACK_WEBHOOK_URL")

    def notify_failure(reason: str) -> None:
        if not webhook:
            logger.error("No SLACK_WEBHOOK_URL; cannot send fallback: %s", reason)
            return
        try:
            post_slack_text(
                f"Workflow failed: {reason}",
                webhook_url=webhook,
            )
        except Exception as e:
            logger.error("Fallback Slack post failed: %s", e)

    try:
        articles = fetch_news_articles()
        if len(articles) < MIN_ARTICLES:
            msg = (
                f"No sufficient headlines today (got {len(articles)}, "
                f"minimum {MIN_ARTICLES})."
            )
            logger.warning(msg)
            if webhook:
                post_slack_text(msg, webhook_url=webhook)
            return

        digest = run_digest(articles)
        text = format_digest_for_slack(digest)
        post_slack_text(text)
        logger.info("Posted digest to Slack")
    except Exception as e:
        logger.exception("Pipeline failed")
        reason = _safe_error_message(e)
        notify_failure(f"Unable to fetch or summarize today's market news. ({reason})")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
