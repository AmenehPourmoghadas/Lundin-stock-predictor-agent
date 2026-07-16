"""
Lundin Mining Daily News Agent
------------------------------
Pulls fresh news (Lundin Mining, Chile copper supply, copper price, geopolitics),
asks Claude to summarize a directional "lean" (not a guarantee), and sends
the result to your WhatsApp.

Run this once per day via cron or a GitHub Actions scheduled workflow.

IMPORTANT: This produces a news-sentiment heuristic, not a financial prediction.
Do not use it as the sole basis for trading decisions.
"""

import os
import json
import datetime
import urllib.parse

import feedparser          # pip install feedparser
import requests             # pip install requests
from anthropic import Anthropic   # pip install anthropic


# ---------- CONFIG ----------

# Anthropic API key (get one at https://console.anthropic.com)
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# CallMeBot config (free WhatsApp sender for personal use)
# Setup: message "I allow callmebot to send me messages" to +34 644 59 71 65
# on WhatsApp, and they will reply with your personal API key.
CALLMEBOT_PHONE = os.environ["CALLMEBOT_PHONE"]     # e.g. "46701234567" (country code, no +, no spaces)
CALLMEBOT_APIKEY = os.environ["CALLMEBOT_APIKEY"]   # the key CallMeBot sent you

# Search topics — edit this list to tune what the agent watches
SEARCH_TOPICS = [
    "Lundin Mining",
    "Codelco copper production",
    "Chile copper supply",
    "copper price today",
    "Strait of Hormuz Iran",
]

MAX_ARTICLES_PER_TOPIC = 5


# ---------- STEP 1: PULL NEWS (free, no API key needed) ----------

def fetch_news(topic: str, max_items: int = 5):
    """Fetch recent headlines for a topic via Google News RSS."""
    query = urllib.parse.quote(topic)
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:max_items]:
        items.append({
            "topic": topic,
            "title": entry.title,
            "published": entry.get("published", ""),
            "source": entry.get("source", {}).get("title", ""),
        })
    return items


def gather_all_news():
    all_items = []
    for topic in SEARCH_TOPICS:
        try:
            all_items.extend(fetch_news(topic, MAX_ARTICLES_PER_TOPIC))
        except Exception as e:
            print(f"Warning: failed to fetch news for '{topic}': {e}")
    return all_items


# ---------- STEP 2: ANALYZE WITH CLAUDE ----------

ANALYSIS_PROMPT = """You are producing a short daily briefing about Lundin Mining
Corporation (LUMI.ST / LUN.TO), a Chile/Brazil/Sweden/Portugal-focused copper,
zinc, gold and nickel miner.

Below are today's headlines across several relevant topics (the stock itself,
Chile copper supply, copper prices, and Middle East geopolitics which affects
risk sentiment and oil/inflation).

Your job:
1. Read the headlines.
2. Judge whether the NEWS BACKDROP today leans bullish, bearish, or neutral
   for Lundin Mining shares — based on real signal only (e.g. Chile mine
   disruptions, copper price moves, company announcements), not vague vibes.
3. Be honest about weak or mixed evidence — "neutral / no clear signal" is a
   valid and often correct answer. Do not force a directional call when the
   headlines don't support one.
4. Output ONLY valid JSON, no markdown fences, no preamble, in this exact shape:

{{
  "date": "{date}",
  "lean": "up" | "down" | "neutral",
  "confidence": "low" | "medium" | "high",
  "reasons": ["short reason 1", "short reason 2", "..."],
  "watch_items": ["thing to watch today/tomorrow, if any"]
}}

Headlines:
{headlines}
"""

def analyze_with_claude(news_items):
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    headlines_text = "\n".join(
        f"- [{item['topic']}] {item['title']} ({item['source']}, {item['published']})"
        for item in news_items
    )

    prompt = ANALYSIS_PROMPT.format(
        date=datetime.date.today().isoformat(),
        headlines=headlines_text or "No headlines retrieved today.",
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    )

    # Defensive parsing in case the model wraps JSON in fences anyway
    cleaned = raw_text.strip().strip("```").replace("json\n", "", 1).strip()
    return json.loads(cleaned)


# ---------- STEP 3: FORMAT + SEND TO WHATSAPP ----------

EMOJI = {"up": "🟢📈", "down": "🔴📉", "neutral": "🟡➖"}

def format_message(analysis: dict) -> str:
    lean = analysis.get("lean", "neutral")
    conf = analysis.get("confidence", "low")
    reasons = analysis.get("reasons", [])
    watch = analysis.get("watch_items", [])

    lines = [
        f"{EMOJI.get(lean, '🟡')} *Lundin Mining Daily Brief* — {analysis.get('date')}",
        f"Lean: *{lean.upper()}*  (confidence: {conf})",
        "",
        "Reasons:",
    ]
    lines += [f"• {r}" for r in reasons] or ["• No strong signal today"]

    if watch:
        lines.append("")
        lines.append("Watch:")
        lines += [f"• {w}" for w in watch]

    lines.append("")
    lines.append("_News-sentiment heuristic only — not financial advice._")
    return "\n".join(lines)


def send_whatsapp_callmebot(message: str):
    """Send via CallMeBot's free WhatsApp API (personal-use, single recipient)."""
    url = "https://api.callmebot.com/whatsapp.php"
    params = {
        "phone": CALLMEBOT_PHONE,
        "text": message,
        "apikey": CALLMEBOT_APIKEY,
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.text


# ---------- MAIN ----------

def main():
    print("Fetching news...")
    news_items = gather_all_news()
    print(f"Got {len(news_items)} headlines.")

    print("Analyzing with Claude...")
    analysis = analyze_with_claude(news_items)
    print(json.dumps(analysis, indent=2))

    message = format_message(analysis)

    print("Sending WhatsApp message...")
    result = send_whatsapp_callmebot(message)
    print("CallMeBot response:", result)


if __name__ == "__main__":
    main()
