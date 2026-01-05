from __future__ import annotations

import numpy as np
import pandas as pd


def classify_regime(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"regime": "unknown", "evidence": {}}
    latest = df.iloc[-1]
    vol_percentile = df["volatility_20"].rank(pct=True).iloc[-1]
    trend_up = latest["ema_20"] > latest["ema_50"] > latest["ema_200"]
    trend_down = latest["ema_20"] < latest["ema_50"] < latest["ema_200"]
    if vol_percentile > 0.7:
        regime = "volatile"
    elif trend_up or trend_down:
        regime = "trend"
    else:
        regime = "range"
    return {
        "regime": regime,
        "evidence": {
            "volatility_percentile": float(vol_percentile),
            "trend_up": bool(trend_up),
            "trend_down": bool(trend_down),
        },
    }
