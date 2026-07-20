from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class Settings:
    model_name: str
    model_token: str
    topics: list[str]
    lookback_hours: int
    max_articles: int
    whatsapp_enabled: bool
    whatsapp_phone: str
    callmebot_api_key: str

def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

def load_yaml(relative_path: str) -> dict:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)

def load_json(relative_path: str) -> dict:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)

def load_settings() -> Settings:
    _load_dotenv()
    base = json.loads(os.getenv("SEARCH_TOPICS_JSON", "[]"))
    manual = [x.strip() for x in os.getenv("ADDITIONAL_TOPICS", "").split(",") if x.strip()]
    topics = list(dict.fromkeys(base + manual))
    return Settings(
        model_name=os.getenv("MODEL_NAME", "openai/gpt-4.1-mini"),
        model_token=os.getenv("GITHUB_MODELS_TOKEN", os.getenv("GITHUB_TOKEN", "")),
        topics=topics,
        lookback_hours=int(os.getenv("NEWS_LOOKBACK_HOURS", "18")),
        max_articles=int(os.getenv("MAX_ARTICLES_PER_QUERY", "8")),
        whatsapp_enabled=os.getenv("WHATSAPP_ENABLED", "false").lower() == "true",
        whatsapp_phone=os.getenv("WHATSAPP_PHONE", ""),
        callmebot_api_key=os.getenv("CALLMEBOT_API_KEY", ""),
    )
