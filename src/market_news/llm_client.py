"""Google Gemini API for top-5 digest (google-genai SDK)."""

from __future__ import annotations

import logging
import os
import re
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from market_news.prompts import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_TEMPERATURE = 0.15
DEFAULT_MAX_RETRIES = 5
INITIAL_BACKOFF_SEC = 28.0


def _is_rate_limit(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if "429" in msg or "resource_exhausted" in msg:
        return True
    if isinstance(exc, genai_errors.ClientError):
        code = getattr(exc, "status_code", None)
        if code == 429:
            return True
    return "quota" in msg and "exceed" in msg


def _retry_after_seconds(exc: BaseException) -> float | None:
    m = re.search(r"retry in ([0-9.]+)s", str(exc), re.I)
    if m:
        try:
            return float(m.group(1)) + 2.0
        except ValueError:
            pass
    return None


def run_digest(articles: list[dict]) -> str:
    """Return model plain-text response (Slack mrkdwn can be applied by caller)."""
    if not articles:
        raise ValueError("No articles to summarize")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")

    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    temperature = float(os.environ.get("LLM_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
    max_retries = int(os.environ.get("GEMINI_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))
    max_retries = max(1, min(max_retries, 8))

    user_content = build_user_message(articles)
    client = genai.Client(api_key=api_key)

    last_err: BaseException | None = None
    for attempt in range(max_retries):
        try:
            logger.info(
                "Calling Gemini model=%s articles=%s attempt=%s/%s",
                model_name,
                len(articles),
                attempt + 1,
                max_retries,
            )
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
        except BaseException as e:
            last_err = e
            if not _is_rate_limit(e) or attempt >= max_retries - 1:
                raise
            wait = _retry_after_seconds(e) or min(
                120.0, INITIAL_BACKOFF_SEC * (attempt + 1)
            )
            logger.warning(
                "Gemini rate limited (429); sleeping %.1fs then retrying (%s/%s)",
                wait,
                attempt + 1,
                max_retries - 1,
            )
            time.sleep(wait)

    if last_err:
        raise last_err
    raise RuntimeError("Gemini call failed without response")
