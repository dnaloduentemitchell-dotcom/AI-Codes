from __future__ import annotations

import redis

from app.core.config import get_settings


def get_redis() -> redis.Redis | None:
    settings = get_settings()
    try:
        return redis.from_url(settings.redis_url)
    except Exception:
        return None
