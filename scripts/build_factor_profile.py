from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf
from lundin_agent.market_data import session
import yaml
import lundin_agent.market_data as market_data
print("market_data loaded from:", market_data.__file__)

ROOT = Path(__file__).resolve().parents[1]

def series_for(symbol: str, days: int = 180) -> pd.Series:
    print("series_for called:", symbol)
    print("session type:", type(session))
    print("session object:", session) 
       
    frame = yf.download(symbol, period=f"{days}d", interval="1d", progress=False, auto_adjust=True, session=session,)
    close = frame["Close"].dropna()
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    return close.pct_change().rename(symbol)

def main() -> None:
    config = yaml.safe_load((ROOT / "config/source_config.yaml").read_text(encoding="utf-8"))
    returns = [series_for(symbol) for symbol in config["market_tickers"].values()]
    frame = pd.concat(returns, axis=1).dropna(how="all")
    target = config["market_tickers"]["lundin_stockholm"]
    correlations = frame.corr()[target].drop(target).dropna().sort_values(ascending=False)

    profile = {
        "status": "quantitative_baseline",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_window_days": 180,
        "method": "Daily-return correlation; association only, not causation.",
        "observed_relationships": [
            {
                "factor_symbol": symbol,
                "correlation": round(float(value), 4),
                "strength": "high" if abs(value) >= 0.6 else "medium" if abs(value) >= 0.3 else "low",
            }
            for symbol, value in correlations.items()
        ],
        "recent_material_events": [],
    }
    path = ROOT / "data/factor_profile.json"
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(json.dumps(profile, indent=2))

if __name__ == "__main__":
    main()
