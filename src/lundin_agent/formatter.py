from __future__ import annotations

EMOJI = {"up": "🟢📈", "down": "🔴📉", "neutral": "🟡➖"}

def format_whatsapp(report: dict) -> str:
    lean = report.get("lean", "neutral")
    lines = [
        f"{EMOJI.get(lean, '🟡')} *Lundin Mining Market Brief*",
        f"Lean: *{lean.upper()}* | Confidence: {report.get('confidence', 'low')}",
        "",
        report.get("summary", "No summary available."),
    ]
    for heading, key in [
        ("Direct company factors", "direct_company_factors"),
        ("Market factors", "market_factors"),
        ("Indirect factors", "indirect_factors"),
        ("Watch next", "watch_items"),
    ]:
        values = report.get(key, [])
        if values:
            lines.extend(["", f"*{heading}:*", *[f"• {value}" for value in values[:5]]])
    urls = report.get("source_urls", [])
    if urls:
        lines.extend(["", "*Evidence:*", *[f"• {url}" for url in urls[:8]]])
    lines.extend(["", "_Research heuristic only — not financial advice._"])
    return "\n".join(lines)
