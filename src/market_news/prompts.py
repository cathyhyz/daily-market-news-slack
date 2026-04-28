"""LLM system prompt from design document (verbatim structure)."""

SYSTEM_PROMPT = """You are an expert financial analyst. Review the following news articles from the past 24 hours. Select the top 5 stories that will have the most significant impact on the US stock market today.

For each of the 5 stories, output a summary in the following strict format:
**[1-5]. [Headline]**
* **Summary:** [1-2 sentences summarizing the news]
* **Why it matters:** [Explain the underlying economic or corporate reason this is important]
* **How it impacts the market:** [Explain specifically which sectors, assets, or indices are likely to move and in what direction]"""


def build_user_message(articles: list[dict]) -> str:
    """Format fetched articles for the model (titles + descriptions only)."""
    lines: list[str] = []
    for i, a in enumerate(articles, start=1):
        title = (a.get("title") or "").strip()
        desc = (a.get("description") or a.get("content") or "").strip()
        url = (a.get("url") or "").strip()
        lines.append(f"Article {i}:\nTitle: {title}\nSummary: {desc}\nURL: {url}\n")
    return "\n".join(lines)
