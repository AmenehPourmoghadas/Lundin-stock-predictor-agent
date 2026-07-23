from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import yaml
import yfinance as yf


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "agent.yaml"


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Config file must contain a YAML object.")

    duration_days = config.get("agent", {}).get("duration_days")

    if not isinstance(duration_days, int) or duration_days < 1:
        raise ValueError("agent.duration_days must be a positive integer.")

    return config


def normalize_dataframe(
    data: pd.DataFrame,
    symbol: str,
) -> pd.DataFrame:
    if data.empty:
        return data

    if isinstance(data.columns, pd.MultiIndex):
        if symbol in data.columns.get_level_values(-1):
            data = data.xs(symbol, axis=1, level=-1)
        elif symbol in data.columns.get_level_values(0):
            data = data.xs(symbol, axis=1, level=0)

    return data


def fetch_market_data(
    symbol: str,
    duration_days: int,
) -> pd.DataFrame:
    data = yf.download(
        tickers=symbol,
        period=f"{duration_days}d",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    data = normalize_dataframe(data, symbol)

    if data.empty:
        raise RuntimeError(f"No market data returned for {symbol}.")

    required_columns = {"Open", "High", "Low", "Close"}

    missing = required_columns.difference(data.columns)

    if missing:
        raise RuntimeError(
            f"Missing required columns for {symbol}: "
            f"{', '.join(sorted(missing))}"
        )

    data = data.dropna(subset=["Close"]).sort_index()

    if data.empty:
        raise RuntimeError(f"No valid closing prices returned for {symbol}.")

    return data.tail(duration_days)


def safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None

    return round(float(value), 6)


def dataframe_to_payload(
    data: pd.DataFrame,
    symbol: str,
    name: str,
) -> dict[str, Any]:
    daily_prices: list[dict[str, Any]] = []

    for index, row in data.iterrows():
        daily_prices.append(
            {
                "date": pd.Timestamp(index).date().isoformat(),
                "open": safe_float(row.get("Open")),
                "high": safe_float(row.get("High")),
                "low": safe_float(row.get("Low")),
                "close": safe_float(row.get("Close")),
                "adjusted_close": safe_float(row.get("Adj Close")),
                "volume": safe_float(row.get("Volume")),
            }
        )

    closes = data["Close"].astype(float)

    first_close = float(closes.iloc[0])
    latest_close = float(closes.iloc[-1])
    absolute_change = latest_close - first_close
    percentage_change = (
        (absolute_change / first_close) * 100 if first_close else 0.0
    )

    daily_returns = closes.pct_change().dropna() * 100

    return {
        "name": name,
        "symbol": symbol,
        "currency": "SEK" if symbol.endswith(".ST") else "USD",
        "trading_day_count": len(data),
        "first_trading_date": daily_prices[0]["date"],
        "last_trading_date": daily_prices[-1]["date"],
        "first_close": round(first_close, 6),
        "latest_close": round(latest_close, 6),
        "period_change": round(absolute_change, 6),
        "period_change_pct": round(percentage_change, 4),
        "highest_close": round(float(closes.max()), 6),
        "lowest_close": round(float(closes.min()), 6),
        "average_close": round(float(closes.mean()), 6),
        "volatility_pct": (
            round(float(daily_returns.std()), 4)
            if len(daily_returns) > 1
            else 0.0
        ),
        "daily_prices": daily_prices,
    }


def write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
        file.write("\n")


def create_chart(
    path: Path,
    duration_days: int,
    lundin_data: pd.DataFrame,
    copper_data: pd.DataFrame,
    lundin_payload: dict[str, Any],
    copper_payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lundin_dates = [
        pd.Timestamp(index).strftime("%d %b")
        for index in lundin_data.index
    ]
    copper_dates = [
        pd.Timestamp(index).strftime("%d %b")
        for index in copper_data.index
    ]

    lundin_closes = lundin_data["Close"].astype(float)
    copper_closes = copper_data["Close"].astype(float)

    figure, axes = plt.subplots(
        2,
        1,
        figsize=(10, 8),
        constrained_layout=True,
    )

    axes[0].plot(
        lundin_dates,
        lundin_closes,
        marker="o",
        linewidth=2,
    )
    axes[0].set_title(
        f"Lundin Mining ({duration_days} trading days)\n"
        f"{lundin_payload['period_change_pct']:+.2f}%"
    )
    axes[0].set_ylabel("Closing price (SEK)")
    axes[0].grid(True, alpha=0.3)
    axes[0].tick_params(axis="x", rotation=45)

    axes[1].plot(
        copper_dates,
        copper_closes,
        marker="o",
        linewidth=2,
    )
    axes[1].set_title(
        f"Copper Futures ({duration_days} trading days)\n"
        f"{copper_payload['period_change_pct']:+.2f}%"
    )
    axes[1].set_ylabel("Closing price (USD)")
    axes[1].grid(True, alpha=0.3)
    axes[1].tick_params(axis="x", rotation=45)

    figure.suptitle(
        "Lundin Mining Market Snapshot",
        fontsize=16,
    )

    figure.savefig(
        path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(figure)


def main() -> int:
    try:
        config = load_config()

        duration_days = config["agent"]["duration_days"]
        generated_at = datetime.now(timezone.utc)
        timestamp = generated_at.strftime("%Y%m%d_%H%M%S")

        lundin_config = config["market"]["lundin"]
        copper_config = config["market"]["copper"]

        lundin_data = fetch_market_data(
            lundin_config["symbol"],
            duration_days,
        )
        copper_data = fetch_market_data(
            copper_config["symbol"],
            duration_days,
        )
        
        common_dates = lundin_data.index.intersection(copper_data.index)

        lundin_data = lundin_data.loc[common_dates]
        copper_data = copper_data.loc[common_dates]

        lundin_payload = dataframe_to_payload(
            lundin_data,
            lundin_config["symbol"],
            lundin_config["name"],
        )
        copper_payload = dataframe_to_payload(
            copper_data,
            copper_config["symbol"],
            copper_config["name"],
        )

        payload = {
            "collector": "market_data",
            "status": "success",
            "generated_at_utc": generated_at.isoformat(),
            "duration_days": duration_days,
            "instruments": {
                "lundin": lundin_payload,
                "copper": copper_payload,
            },
        }

        output_dir = REPO_ROOT / "data"

        json_path = output_dir / f"market_data_{timestamp}.json"
        chart_path = output_dir / f"market_data_{timestamp}.png"

        write_json(json_path, payload)

        create_chart(
            chart_path,
            duration_days,
            lundin_data,
            copper_data,
            lundin_payload,
            copper_payload,
        )

        print(f"Created: {json_path}")
        print(f"Created: {chart_path}")

        return 0

    except Exception as exception:
        print(
            f"Market data collection failed: {exception}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
