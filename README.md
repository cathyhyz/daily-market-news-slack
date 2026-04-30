# Automated daily market news to Slack

Python workflow: fetch headlines from **RSS/Atom feeds** (no NewsAPI key), ask **Google Gemini** for the top 5 US market-moving stories using the prompt from the design doc, post to Slack via Incoming Webhook. Intended to run on **GitHub Actions** on weekdays.

## Prerequisites

- **RSS feeds** — defaults are built in (BBC Business + Dow Jones / MarketWatch pulse). Override with env **`RSS_FEEDS`** (comma-separated URLs) if you want other sources. Respect each publisher’s **terms of use** and crawling etiquette.
- [Google AI Studio](https://aistudio.google.com/apikey) (or Google Cloud) **Gemini API key**.
- [Slack Incoming Webhook](https://api.slack.com/messaging/webhooks) URL for your channel.

## Security

- **Never commit API keys** or paste them into chat, tickets, or screenshots. This repo’s `.gitignore` ignores `.env` to reduce accidents.
- If a key was exposed, **rotate it** in the provider’s dashboard and update GitHub **Secrets** / your local `.env` only on your machine.

## GitHub repository secrets

| Secret | Description |
|--------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `SLACK_WEBHOOK_URL` | Full Slack Incoming Webhook URL |

Optional **repository variables** (Settings → Secrets and variables → **Actions** → **Variables**):

| Variable | Description |
|----------|-------------|
| `RSS_FEEDS` | Comma-separated RSS/Atom URLs (overrides built-in defaults) |
| `NEWS_MAX_ITEMS` | Max items to send to the model after merge/dedupe (default `40`) |
| `GEMINI_MODEL`, `LLM_TEMPERATURE`, `MIN_ARTICLES` | Same as before |

You can set **`RSS_USER_AGENT`** in the environment if a feed requires a specific client string.

## Local run

Either export variables in your shell, or copy [`.env.example`](.env.example) to `.env`, fill in values, then:

```bash
set -a && source .env && set +a   # bash/zsh: load .env into environment
```

```bash
cd /path/to/this/repo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Ensure GEMINI_API_KEY and SLACK_WEBHOOK_URL are set; RSS_FEEDS optional
PYTHONPATH=src python -m market_news
```

## Schedule (GitHub Actions cron is UTC)

The workflow [`.github/workflows/daily-market-news.yml`](.github/workflows/daily-market-news.yml) uses **Monday–Friday** only (`1-5`).

GitHub does not interpret local timezones; the `schedule` event is **UTC**.

| Desired local time | Region | Example UTC cron (see workflow file for actual) |
|--------------------|--------|---------------------------------------------------|
| 09:00 Mon–Fri | US Eastern (EST, ~Nov–Mar) | `0 14 * * 1-5` |
| 09:00 Mon–Fri | US Eastern (EDT, ~Mar–Nov) | `0 13 * * 1-5` |
| 09:00 Mon–Fri | US Pacific (PST) | `0 17 * * 1-5` |
| 09:00 Mon–Fri | US Pacific (PDT) | `0 16 * * 1-5` |

**DST note:** Pick the UTC offset that matches your target season, or adjust the cron twice per year. The workflow YAML comments document the default (US Eastern morning).

## Manual test in GitHub

Actions → **Daily market news** → **Run workflow**.

## Tests

```bash
pip install -r requirements.txt
PYTHONPATH=src pytest tests/ -q
```
