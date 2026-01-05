from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from app.ingestion.base import MacroProvider


class DemoMacroProvider(MacroProvider):
    def __init__(self, data_path: str = "data/demo_macro_events.csv") -> None:
        self.data_path = Path(data_path)

    def fetch_events(self, since: datetime | None) -> list[dict]:
        if not self.data_path.exists():
            return []
        data = pd.read_csv(self.data_path, parse_dates=["time"])
        if since is not None:
            data = data[data["time"] > since]
        return data.sort_values("time").to_dict(orient="records")
