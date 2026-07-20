from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lundin_agent.analyzer import analyze
from lundin_agent.collectors.gdelt import fetch_gdelt
from lundin_agent.collectors.google_news import fetch_google_news
from lundin_agent.collectors.lundin_official import fetch_lundin_official
from lundin_agent.config import load_json, load_settings, load_yaml
from lundin_agent.deduplicator import deduplicate
from lundin_agent.formatter import format_whatsapp
from lundin_agent.market_data import fetch_market_snapshot
from lundin_agent.whatsapp import send_callmebot

def main() -> None:
    settings = load_settings()
    company_profile = load_yaml("config/company_profile.yaml")
    sources = load_yaml("config/source_config.yaml")
    factor_profile = load_json("data/factor_profile.json")

    articles = []
    errors = []
    try:
        articles.extend(fetch_lundin_official())
    except Exception as exc:
        errors.append(f"lundin_official: {exc}")

    for topic in settings.topics:
        for name, collector in (
            ("google_news", lambda: fetch_google_news(topic, settings.max_articles)),
            ("gdelt", lambda: fetch_gdelt(topic, settings.max_articles, settings.lookback_hours)),
        ):
            try:
                articles.extend(collector())
            except Exception as exc:
                errors.append(f"{name}/{topic}: {exc}")

    articles = deduplicate(articles)
    market = fetch_market_snapshot(sources["market_tickers"])

    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "company_profile": company_profile,
        "historical_factor_profile": factor_profile,
        "market_snapshot": market,
        "articles": [item.to_dict() for item in articles[:80]],
        "collection_errors": errors,
        "instructions": {
            "goal": "Assess today's directional news and market backdrop for Lundin Mining.",
            "requirements": [
                "Use direct and indirect drivers.",
                "Prefer official company announcements and named evidence.",
                "Do not force a directional lean.",
                "Include only source URLs found in the supplied articles.",
            ],
        },
    }

    report = analyze(evidence, settings.model_token, settings.model_name)
    report["generated_at"] = evidence["generated_at"]
    report["market_snapshot"] = market
    report["collection_errors"] = errors
    report["article_count"] = len(articles)

    output_dir = ROOT / "data" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{datetime.now(timezone.utc):%Y-%m-%dT%H-%M-%SZ}.json"
    output_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    message = format_whatsapp(report)
    print(message)
    print(f"\nSaved report: {output_file}")

    if settings.whatsapp_enabled:
        response = send_callmebot(message, settings.whatsapp_phone, settings.callmebot_api_key)
        print("CallMeBot response:", response)
    else:
        print("WhatsApp disabled; local test completed without sending.")

if __name__ == "__main__":
    main()
