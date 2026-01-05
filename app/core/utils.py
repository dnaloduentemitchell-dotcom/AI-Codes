from __future__ import annotations

import hashlib
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
