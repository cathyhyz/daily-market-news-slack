"""Google Gemini API for top-5 digest (google-genai SDK)."""

from __future__ import annotations

import logging
import os

from google import genai
from google.genai import types

from market_news.prompts import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_TEMPERATURE = 0.15


def run_digest(articles: list[dict]) -> str:
    """Return model plain-text response (Slack mrkdwn can be applied by caller)."""
    if not articles:
        raise ValueError("No articles to summarize")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")

    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    temperature = float(os.environ.get("LLM_TEMPERATURE", str(DEFAULT_TEMPERATURE)))

    user_content = build_user_message(articles)
    client = genai.Client(api_key=api_key)

    logger.info("Calling Gemini model=%s articles=%s", model_name, len(articles))
    response = client.models.generate_content(
        model=model_name,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=temperature,
        ),
    )
    try:
        raw = response.text
    except ValueError as e:
        raise RuntimeError("Empty or blocked Gemini response") from e
    text = (raw or "").strip()
    if not text:
        raise RuntimeError("Empty completion from Gemini")
    return text
