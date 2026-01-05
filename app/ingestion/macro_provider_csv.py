from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from app.ingestion.base import MacroProvider


class CsvMacroProvider(MacroProvider):
    def __init__(self, csv_path: str) -> None:
        self.csv_path = Path(csv_path)

    def fetch_events(self, since: datetime | None) -> list[dict]:
        if not self.csv_path.exists():
            return []
        data = pd.read_csv(self.csv_path, parse_dates=["time"])
        if since is not None:
            data = data[data["time"] > since]
        return data.sort_values("time").to_dict(orient="records")
