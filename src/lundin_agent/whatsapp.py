from __future__ import annotations
import requests

def send_callmebot(message: str, phone: str, api_key: str) -> str:
    if not phone or not api_key:
        raise RuntimeError("WHATSAPP_PHONE or CALLMEBOT_API_KEY is missing.")
    response = requests.get(
        "https://api.callmebot.com/whatsapp.php",
        params={"phone": phone, "text": message, "apikey": api_key},
        timeout=30,
    )
    response.raise_for_status()
    return response.text
