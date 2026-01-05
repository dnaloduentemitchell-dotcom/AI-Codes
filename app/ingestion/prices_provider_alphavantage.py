from __future__ import annotations

from datetime import datetime

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ingestion.base import PriceProvider


class AlphaVantagePriceProvider(PriceProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def fetch_bars(self, symbol: str, timeframe: str, start: datetime | None) -> list[dict]:
        interval = "1min" if timeframe == "1m" else "5min"
        params = {
            "function": "FX_INTRADAY",
            "from_symbol": symbol[:3],
            "to_symbol": symbol[3:],
            "interval": interval,
            "apikey": self.api_key,
            "outputsize": "compact",
        }
        response = requests.get("https://www.alphavantage.co/query", params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
        series_key = f"Time Series FX ({interval})"
        if series_key not in payload:
            return []
        data = []
        for ts_str, values in payload[series_key].items():
            ts = datetime.fromisoformat(ts_str)
            if start and ts <= start:
                continue
            data.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "ts": ts,
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": 0.0,
                }
            )
        return sorted(data, key=lambda row: row["ts"])
