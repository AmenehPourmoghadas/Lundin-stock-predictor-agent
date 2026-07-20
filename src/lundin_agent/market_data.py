from __future__ import annotations
import math
from curl_cffi import requests
from lundin_agent.ssl_config import get_ca_bundle
import yfinance as yf
'''class VerifiedSession(requests.Session):
    def request(self, method, url, **kwargs):
        kwargs.setdefault("verify", get_ca_bundle())
        return super().request(method, url, **kwargs)
'''
class VerifiedSession(requests.Session):
    def request(self, method, url, **kwargs):
        print("VerifiedSession request:", method, url)
        print("verify before override:", kwargs.get("verify"))

        kwargs["verify"] = get_ca_bundle()
        print("verify after override:", kwargs["verify"])
        return super().request(method, url, **kwargs)

session = VerifiedSession()

def _clean(value):
    try:
        numeric = float(value)
        return None if math.isnan(numeric) else round(numeric, 4)
    except (TypeError, ValueError):
        return None

def fetch_market_snapshot(tickers: dict[str, str]) -> dict:
    output: dict[str, dict] = {}
    for name, symbol in tickers.items():
        try:
            frame = yf.download(symbol, period="10d", interval="1d", progress=False, auto_adjust=True, session=session,)
            closes = frame["Close"].dropna()
            if hasattr(closes, "columns"):
                closes = closes.iloc[:, 0]
            latest = _clean(closes.iloc[-1]) if len(closes) else None
            previous = _clean(closes.iloc[-2]) if len(closes) > 1 else None
            change_pct = None
            if latest is not None and previous not in (None, 0):
                change_pct = round((latest / previous - 1) * 100, 3)
            output[name] = {"symbol": symbol, "latest": latest, "previous": previous, "change_pct": change_pct}
        except Exception as exc:
            output[name] = {"symbol": symbol, "error": str(exc)}
    return output
