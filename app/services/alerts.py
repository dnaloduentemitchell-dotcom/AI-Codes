from __future__ import annotations

from typing import Any


def format_alert(message: str, payload: dict[str, Any]) -> str:
    return f"{message}: {payload}"
