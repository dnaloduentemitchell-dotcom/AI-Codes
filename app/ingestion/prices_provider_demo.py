from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from app.ingestion.base import PriceProvider


class DemoPriceProvider(PriceProvider):
    def __init__(self, data_path: str = "data/demo_prices.csv") -> None:
        self.data_path = Path(data_path)

    def fetch_bars(self, symbol: str, timeframe: str, start: datetime | None) -> list[dict]:
        if not self.data_path.exists():
            return []
        data = pd.read_csv(self.data_path, parse_dates=["ts"])
        data = data[data["symbol"] == symbol]
        if start is not None:
            data = data[data["ts"] > start]
        if timeframe != "1m":
            data = data[data["timeframe"] == timeframe]
        return data.sort_values("ts").to_dict(orient="records")
