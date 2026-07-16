# Lundin Mining Daily WhatsApp Brief — Setup Guide

A small agent that reads Lundin Mining / Chile copper / Iran-conflict news each day,
asks Claude to produce a directional lean (up / down / neutral), and texts you
the result on WhatsApp.

**This is a news-sentiment heuristic, not a trading signal.** Use it as a daily
briefing, not as investment advice.

---

## 1. Get an Anthropic API key

1. Go to https://console.anthropic.com and create an account.
2. Add billing (pay-as-you-go — this script uses very little, a few cents/month).
3. Create an API key under "API Keys". Copy it.

## 2. Get a free WhatsApp sender key (CallMeBot)

CallMeBot lets you send yourself WhatsApp messages for free, no business account needed.

1. Save this contact in your phone: **+34 644 59 71 65**
2. Send it this exact WhatsApp message: `I allow callmebot to send me messages`
3. Within a minute or two you'll get a reply with your personal **API key**.
4. Note your own phone number in international format with no `+` and no spaces
   (e.g. Swedish number `+46 70 123 45 67` → `46701234567`).

*(This is fine for personal daily use. If you ever want a more "official"/robust
setup — multiple recipients, guaranteed delivery SLAs — use Twilio's WhatsApp
API instead; see the note at the bottom.)*

## 3. Get the code running

Files you need (all in this folder):
- `lundin_agent.py` — the agent itself
- `requirements.txt` — Python dependencies

Install dependencies:
```bash
pip install -r requirements.txt
```

Set your credentials as environment variables:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export CALLMEBOT_PHONE="46701234567"
export CALLMEBOT_APIKEY="123456"
```

Test it manually once:
```bash
python lundin_agent.py
```

You should see it print the fetched headlines, the JSON analysis, and then
get a WhatsApp message within a few seconds.

## 4. Schedule it to run daily

**Option A — GitHub Actions (recommended, free, no server to maintain):**

1. Create a new GitHub repo (can be private).
2. Add `lundin_agent.py` and `requirements.txt` to the repo root.
3. Add `daily_lundin_brief.yml` to `.github/workflows/daily_lundin_brief.yml`.
4. In the repo: Settings → Secrets and variables → Actions → add:
   - `ANTHROPIC_API_KEY`
   - `CALLMEBOT_PHONE`
   - `CALLMEBOT_APIKEY`
5. That's it — GitHub runs it daily at the time set in the cron line
   (`0 7 * * *` = 07:00 UTC; edit to your preferred time).
6. You can also trigger it manually anytime from the repo's "Actions" tab
   ("Run workflow" button), thanks to `workflow_dispatch`.

**Option B — cron on your own machine / a cheap VPS:**

```bash
crontab -e
# add this line (runs daily at 07:00 local time):
0 7 * * * cd /path/to/folder && /usr/bin/python3 lundin_agent.py >> agent.log 2>&1
```

## 5. Customize it

- Edit `SEARCH_TOPICS` in `lundin_agent.py` to add/remove things to watch
  (e.g. add "Candelaria mine" or a specific competitor).
- Edit `ANALYSIS_PROMPT` if you want a different output style, more/less detail,
  or to track a different stock entirely.
- Consider logging each day's `analysis` JSON to a file or spreadsheet so that,
  after a few months, you can check how often the "lean" actually matched what
  the stock did — that's the only real way to find out if this is useful
  or just noise.

## Note on WhatsApp providers

| Provider | Cost | Setup effort | Best for |
|---|---|---|---|
| **CallMeBot** (used here) | Free | ~2 minutes | Personal use, one recipient |
| **Twilio WhatsApp API** | Pay-per-message (cheap) | ~30 min, needs Twilio account + WhatsApp sandbox/business approval | More reliable, multiple recipients, production use |
| **Meta WhatsApp Cloud API** | Free tier available | Most setup (business verification) | Sending at scale |

For a single-person daily brief, CallMeBot is the fastest way to get this working today.

---

### Reminder

Stock-moving news is unpredictable by nature, and by the time a headline is
public, markets have often already reacted. Treat this agent's output as a
"here's what's in the news today" summary — a starting point for your own
judgment, not a signal to act on automatically.
