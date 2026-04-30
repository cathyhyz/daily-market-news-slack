"""LLM system prompt from design document (verbatim structure)."""

import os

SYSTEM_PROMPT = """You are an expert financial analyst. Review the following news articles from the past 24 hours. Select the top 5 stories that will have the most significant impact on the US stock market today.

For each of the 5 stories, output a summary in the following strict format:
**[1-5]. [Headline]**
* **Summary:** [1-2 sentences summarizing the news]
* **Why it matters:** [Explain the underlying economic or corporate reason this is important]
* **How it impacts the market:** [Explain specifically which sectors, assets, or indices are likely to move and in what direction]"""


def build_user_message(articles: list[dict]) -> str:
    """Format fetched articles for the model (titles + descriptions only)."""
    lines: list[str] = []
    # Keeps free-tier Gemini prompts smaller (RPM / tokens per minute).
    cap = int(os.environ.get("NEWS_PROMPT_DESC_CHARS", "350"))
    cap = max(80, min(cap, 2000))
    for i, a in enumerate(articles, start=1):
        title = (a.get("title") or "").strip()
        desc = (a.get("description") or a.get("content") or "").strip()
        if len(desc) > cap:
            head = desc[: cap - 1]
            cut = head.rsplit(" ", 1)[0]
            desc = (cut if len(cut) > cap // 3 else head) + "…"
        url = (a.get("url") or "").strip()
        lines.append(f"Article {i}:\nTitle: {title}\nSummary: {desc}\nURL: {url}\n")
    return "\n".join(lines)
