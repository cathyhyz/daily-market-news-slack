Here is a complete design document for your automated stock market news workflow. I have broken it down by architecture, data flow, technology stack options, and implementation steps.

---

## Design Document: Automated Daily Market News to Slack

### 1. Objective
To build an automated daily workflow that triggers at 9:00 AM, retrieves the latest financial and macroeconomic news, uses an AI model to identify the top 5 market-moving stories, and delivers a formatted summary (including the "why" and "how" of the market impact) directly to a designated Slack channel.

### 2. System Architecture & Components
The system consists of five distinct logical components:
* **Scheduler:** A time-based trigger that initiates the workflow exactly at 9:00 AM every day.
* **Data Source (News API):** An aggregator that fetches the latest financial news articles published over the last 24 hours.
* **Processing Engine (LLM):** An AI model tasked with reading the raw news data, scoring/selecting the top 5 most impactful stories, and generating the specific summaries.
* **Delivery Mechanism (Slack API):** A webhook or bot integration that posts the final formatted text to your Slack workspace.
* **Orchestrator:** The host environment (either custom code or a no-code platform) that ties all these APIs together and manages the flow of data.

---

### 3. Data Flow
1.  **Trigger Event:** The Scheduler hits 9:00 AM (specify your local timezone) and awakens the Orchestrator.
2.  **Fetch Data:** The Orchestrator makes an HTTP GET request to the News API to pull the top 20–30 financial headlines and summaries from the past 24 hours.
3.  **Analyze & Summarize:** The Orchestrator sends the compiled news data to the LLM via an API call, using a strict prompt (see *Prompt Engineering* below).
4.  **Format:** The LLM returns a structured response containing the top 5 news items, focusing specifically on the *why* and *how* of the market impact.
5.  **Deliver:** The Orchestrator takes the LLM's text and formats it into a Slack-friendly JSON payload. It sends an HTTP POST request to the Slack Incoming Webhook URL.
6.  **End:** The message appears in your Slack channel.

---

### 4. Technology Stack Options

You can build this using either a **Custom Code** approach or a **No-Code** approach. 

#### Option A: Custom Code (Recommended for flexibility and cost)
* **Orchestrator & Scheduler:** GitHub Actions (free cron jobs) or AWS Lambda + Amazon EventBridge.
* **Language:** Python.
* **News Source:** [NewsAPI.org](https://newsapi.org/), [Finnhub](https://finnhub.io/), or [Alpha Vantage](https://www.alphavantage.co/).
* **AI Model:** Google Gemini API or OpenAI API (gpt-4o-mini is highly cost-effective for daily text processing).
* **Slack Integration:** Slack Incoming Webhooks (simplest) or the official Slack Python SDK.

#### Option B: No-Code (Recommended for speed of deployment)
* **Platform:** Zapier or Make.com.
* **Trigger:** Zapier/Make built-in "Schedule" module (Every day at 9:00 AM).
* **News Source:** Built-in RSS by Zapier (plugging in feeds from Bloomberg, CNBC, or Reuters).
* **AI Model:** Zapier/Make's native OpenAI or Anthropic integration modules.
* **Slack Integration:** Zapier/Make's native Slack module ("Send Channel Message").

---

### 5. Implementation Details

#### A. Prompt Engineering (The Brains of the Operation)
To ensure the AI extracts exactly what you want, the system prompt sent to the LLM should look something like this:

> **System Prompt:**
> "You are an expert financial analyst. Review the following news articles from the past 24 hours. Select the top 5 stories that will have the most significant impact on the US stock market today. 
> 
> For each of the 5 stories, output a summary in the following strict format:
> **[1-5]. [Headline]**
> * **Summary:** [1-2 sentences summarizing the news]
> * **Why it matters:** [Explain the underlying economic or corporate reason this is important]
> * **How it impacts the market:** [Explain specifically which sectors, assets, or indices are likely to move and in what direction]"

#### B. Slack Payload Formatting
To make the message readable in Slack, utilize Slack's "mrkdwn" (markdown) formatting. The JSON payload sent to the webhook will look like this:

```json
{
  "text": "Good morning! ☕ Here are the top 5 market-moving stories for today:\n\n*1. Fed Announces Surprise Rate Cut*\n* *Summary:* ...\n* *Why it matters:* ...\n* *How it impacts the market:* ..."
}
```

---

### 6. Edge Cases & Error Handling
* **Empty News Days (Weekends/Holidays):** Financial news is slow on weekends. You should configure the scheduler to run Monday–Friday only.
* **API Timeouts or Rate Limits:** If the News API or LLM API fails, the orchestrator should catch the error and send a fallback Slack message (e.g., *"⚠️ Workflow failed: Unable to fetch today's market news. Check API limits."*).
* **Hallucinations:** Setting the LLM's `temperature` parameter to a low number (e.g., `0.1` or `0.2`) ensures it sticks strictly to the provided news text and doesn't invent financial narratives.