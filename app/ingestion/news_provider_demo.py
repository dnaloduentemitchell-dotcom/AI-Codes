from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from app.ingestion.base import NewsProvider


class DemoNewsProvider(NewsProvider):
    def __init__(self, data_path: str = "data/demo_news.csv") -> None:
        self.data_path = Path(data_path)

    def fetch_news(self, since: datetime | None) -> list[dict]:
        if not self.data_path.exists():
            return []
        data = pd.read_csv(self.data_path, parse_dates=["published_at"])
        if since is not None:
            data = data[data["published_at"] > since]
        return data.sort_values("published_at").to_dict(orient="records")
