from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def build_explanation(latest_row: pd.Series, probabilities: dict[str, float], regime: dict) -> dict[str, Any]:
    top_features = []
    for name, value in latest_row.items():
        if name in {"ts", "open", "high", "low", "close", "volume"}:
            continue
        top_features.append({"name": name, "value": float(value)})
    top_features = sorted(top_features, key=lambda item: abs(item["value"]), reverse=True)[:5]
    return {
        "top_features": top_features,
        "probabilities": probabilities,
        "regime": regime,
        "sentiment_score": float(latest_row.get("news_sentiment_24h", 0.0)),
        "macro_risk_minutes": float(latest_row.get("minutes_to_high_impact_usd", 0.0)),
        "recent_news": [],
        "disclaimer": "Signals are probabilistic analytics, not financial advice.",
    }
