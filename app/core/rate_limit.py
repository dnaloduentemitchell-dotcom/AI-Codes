from __future__ import annotations

from datetime import datetime, timezone

from app.core.cache import get_redis


def allow_run(name: str, min_interval_seconds: int) -> bool:
    client = get_redis()
    if client is None:
        return True
    key = f"rate_limit:{name}"
    now = datetime.now(timezone.utc).timestamp()
    try:
        last = client.get(key)
        if last and now - float(last) < min_interval_seconds:
            return False
        client.set(key, now, ex=min_interval_seconds)
    except Exception:
        return True
    return True
