from __future__ import annotations
import json
import requests

ENDPOINT = "https://models.github.ai/inference/chat/completions"

SYSTEM_PROMPT = """You are a cautious market-intelligence analyst for Lundin Mining.
Use only the supplied evidence. Separate direct company events, commodity/macro
drivers and geopolitical context. Never claim causation without evidence.
Return valid JSON only. This is research, not financial advice."""

def analyze(evidence: dict, token: str, model: str) -> dict:
    if not token:
        raise RuntimeError("GITHUB_MODELS_TOKEN is missing. Add it to .env for local runs.")
    schema = {
        "name": "lundin_daily_brief",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "lean": {"type": "string", "enum": ["up", "down", "neutral"]},
                "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                "summary": {"type": "string"},
                "direct_company_factors": {"type": "array", "items": {"type": "string"}},
                "market_factors": {"type": "array", "items": {"type": "string"}},
                "indirect_factors": {"type": "array", "items": {"type": "string"}},
                "watch_items": {"type": "array", "items": {"type": "string"}},
                "source_urls": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "lean", "confidence", "summary", "direct_company_factors",
                "market_factors", "indirect_factors", "watch_items", "source_urls"
            ],
        },
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "max_tokens": 1200,
        "response_format": {"type": "json_schema", "json_schema": schema},
    }
    response = requests.post(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2026-03-10",
        },
        json=body,
        timeout=90,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)
