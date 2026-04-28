# Automated daily market news to Slack

Python workflow: fetch recent business headlines (NewsAPI), ask **Google Gemini** for the top 5 US market-moving stories using the prompt from the design doc, post to Slack via Incoming Webhook. Intended to run on **GitHub Actions** on weekdays.

## Prerequisites

- [NewsAPI.org](https://newsapi.org/) API key (developer tier is enough for daily runs).
- [Google AI Studio](https://aistudio.google.com/apikey) (or Google Cloud) **Gemini API key**.
- [Slack Incoming Webhook](https://api.slack.com/messaging/webhooks) URL for your channel.

## Security

- **Never commit API keys** or paste them into chat, tickets, or screenshots. This repo’s `.gitignore` ignores `.env` to reduce accidents.
- If a key was exposed, **rotate it** in the provider’s dashboard (NewsAPI: account → regenerate) and update GitHub **Secrets** / your local `.env` only on your machine.

## GitHub repository secrets

| Secret | Description |
|--------|-------------|
| `NEWS_API_KEY` | NewsAPI key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `SLACK_WEBHOOK_URL` | Full Slack webhook URL |

Optional **repository variables** (or set as env in workflow): `NEWS_QUERY`, `NEWS_PAGE_SIZE`, `GEMINI_MODEL`, `LLM_TEMPERATURE`, `MIN_ARTICLES`.

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
# Ensure NEWS_API_KEY, GEMINI_API_KEY, SLACK_WEBHOOK_URL are set (see above)
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
