from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable


class PriceProvider(ABC):
    @abstractmethod
    def fetch_bars(self, symbol: str, timeframe: str, start: datetime | None) -> list[dict]:
        raise NotImplementedError


class NewsProvider(ABC):
    @abstractmethod
    def fetch_news(self, since: datetime | None) -> list[dict]:
        raise NotImplementedError


class MacroProvider(ABC):
    @abstractmethod
    def fetch_events(self, since: datetime | None) -> list[dict]:
        raise NotImplementedError
