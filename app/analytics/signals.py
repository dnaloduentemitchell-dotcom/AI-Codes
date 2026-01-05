from __future__ import annotations

from typing import Any

import numpy as np


def label_from_probability(prob_bull: float, prob_bear: float, neutral_threshold: float = 0.45) -> str:
    if prob_bull >= neutral_threshold and prob_bull > prob_bear:
        return "Bullish"
    if prob_bear >= neutral_threshold and prob_bear > prob_bull:
        return "Bearish"
    return "Neutral"


def build_confidence(probabilities: dict[str, float]) -> float:
    return float(max(probabilities.values()))


def confidence_reason(regime: str, sentiment_score: float, volatility: float) -> str:
    parts = []
    if regime == "trend":
        parts.append("Trend regime supports directional bias")
    if sentiment_score > 0.2:
        parts.append("Positive news sentiment")
    elif sentiment_score < -0.2:
        parts.append("Negative news sentiment")
    if volatility > 0.7:
        parts.append("Elevated volatility")
    return "; ".join(parts) or "Mixed signals; confidence muted"
