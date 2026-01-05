from __future__ import annotations

from datetime import datetime, timezone

import feedparser
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ingestion.base import NewsProvider


class RssNewsProvider(NewsProvider):
    def __init__(self, urls: list[str]) -> None:
        self.urls = urls

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def fetch_news(self, since: datetime | None) -> list[dict]:
        items: list[dict] = []
        for url in self.urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                published = entry.get("published_parsed")
                if published:
                    published_at = datetime(*published[:6], tzinfo=timezone.utc)
                else:
                    published_at = datetime.now(timezone.utc)
                if since and published_at <= since:
                    continue
                items.append(
                    {
                        "source": feed.feed.get("title", url),
                        "published_at": published_at,
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "url": entry.get("link", ""),
                    }
                )
        return items
