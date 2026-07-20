from lundin_agent.formatter import format_whatsapp

def test_formatter_contains_lean():
    text = format_whatsapp({
        "lean": "up",
        "confidence": "medium",
        "summary": "Copper strengthened.",
        "direct_company_factors": [],
        "market_factors": [],
        "indirect_factors": [],
        "watch_items": [],
        "source_urls": [],
    })
    assert "UP" in text
    assert "Copper strengthened." in text
