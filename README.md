# Lundin Mining Market Intelligence Agent

A cost-conscious Python agent as a personal AI investment assistant that filters thousands of daily news items into a single actionable WhatsApp briefing.

Every morning it would:

Collect news from multiple trusted sources (Google News, GDELT, Lundin Mining, etc.).
Identify events relevant to Lundin Mining and indirect drivers (copper prices, Chile, geopolitics, competitors).
Use an LLM to distinguish signal from noise and explain why a story matters.
Estimate whether the overall news flow is Bullish / Neutral / Bearish for the stock.
Send a concise WhatsApp message with the key news, reasoning, confidence, and links—so you could understand the likely market impact in under a minute, without reading dozens of articles.

## What it monitors

- Lundin Mining official announcements
- GDELT global news
- Google News RSS discovery
- `LUMI.ST`, `LUN.TO`, copper, gold, oil, FX and broad market indices
- Persistent repository topics plus user-supplied workflow topics
- A 180-day quantitative factor baseline

## Cost-efficiency design

This portfolio implementation avoids persistent cloud infrastructure and paid
news subscriptions. GitHub Actions supplies scheduled compute. GDELT, Google
News RSS and Lundin Mining's public investor-relations pages supply news.
`yfinance` supplies research-grade market data. GitHub Models supplies free,
rate-limited model inference for prototyping. CallMeBot is used for personal
WhatsApp delivery.

Limitations: GitHub Models free quotas can change; Google News RSS is not a
formally supported search API; `yfinance` is not an official exchange feed; and
the output is not financial advice or an automated trading signal.

## Scheduled runs

The workflow runs Monday-Friday at 07:17 and 15:17 Europe/Stockholm. It can also
be run manually with additional monitoring topics.

## Local execution

1. Copy `.env.example` to `.env`.
2. Add a fine-grained GitHub token with `models:read`.
3. Set `WHATSAPP_ENABLED=false` for the first test.
4. Install dependencies and run tests.
5. Run `python scripts/build_factor_profile.py`.
6. Run `python scripts/run_daily_brief.py`.

See the repository workflow files (Sercerts) for GitHub Actions configuration.


