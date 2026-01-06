from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


@dataclass
class NewsAnalysis:
    summary: str
    sentiment_score: float
    sentiment_label: str
    impact_level: str
    impacted_assets: list[str]
    rationale: str
    topics: dict
    is_fundamental: bool


class RuleBasedNewsAnalyzer:
    def __init__(self) -> None:
        self._sentiment = SentimentIntensityAnalyzer()

    def analyze(self, title: str, summary: str, source: str = "") -> NewsAnalysis:
        text = f"{title}. {summary}".strip()
        sentiment_score = self._sentiment.polarity_scores(text).get("compound", 0.0)
        sentiment_label = _label_sentiment(sentiment_score)
        topics = _detect_topics(text)
        impacted_assets = _map_impacted_assets(text, topics)
        impact_level = _impact_level(text, topics)
        rationale = _build_rationale(impacted_assets, topics, sentiment_label)
        analysis_summary = _compress_summary(summary or title)
        is_fundamental = bool(topics.get("macro")) or bool(topics.get("rates")) or bool(topics.get("inflation"))
        return NewsAnalysis(
            summary=analysis_summary,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            impact_level=impact_level,
            impacted_assets=impacted_assets,
            rationale=rationale,
            topics=topics,
            is_fundamental=is_fundamental,
        )


_KEYWORD_TOPICS = {
    "inflation": ["cpi", "inflation", "pce", "ppi", "price pressures", "core prices"],
    "rates": ["rate hike", "rate cut", "interest rate", "fomc", "ecb", "boj", "boe", "policy rate"],
    "growth": ["gdp", "pm i", "manufacturing", "services", "retail sales", "jobs", "nfp"],
    "geopolitics": ["war", "conflict", "sanction", "missile", "ceasefire", "geopolitical"],
    "risk": ["risk-on", "risk-off", "equities", "stocks", "bond yields", "volatility"],
    "commodities": ["oil", "crude", "gold", "silver", "copper", "commodity"],
}

_ASSET_RULES = {
    "inflation": ["XAUUSD", "DXY", "US10Y"],
    "rates": ["EURUSD", "GBPUSD", "USDJPY", "DXY"],
    "growth": ["USDJPY", "EURUSD", "GBPUSD", "SPX"],
    "geopolitics": ["XAUUSD", "USOIL", "XAGUSD"],
    "risk": ["SPX", "NAS100", "USDJPY"],
    "commodities": ["XAUUSD", "USOIL", "XAGUSD"],
}

_ASSET_ALIASES = {
    "xau/usd": "XAUUSD",
    "gold": "XAUUSD",
    "eur/usd": "EURUSD",
    "gbp/usd": "GBPUSD",
    "usd/jpy": "USDJPY",
    "dxy": "DXY",
    "us dollar": "DXY",
    "oil": "USOIL",
    "brent": "USOIL",
    "wti": "USOIL",
    "silver": "XAGUSD",
    "s&p": "SPX",
    "nasdaq": "NAS100",
    "nifty": "NIFTY",
}


def _compress_summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return " ".join(sentences[:2]) if len(sentences) > 2 else cleaned


def _label_sentiment(score: float) -> str:
    if score >= 0.2:
        return "bullish"
    if score <= -0.2:
        return "bearish"
    return "neutral"


def _detect_topics(text: str) -> dict:
    lowered = text.lower()
    topics = {}
    for topic, keywords in _KEYWORD_TOPICS.items():
        hits = sum(1 for key in keywords if key in lowered)
        if hits:
            topics[topic] = hits
    if not topics:
        topics["macro"] = 0
    return topics


def _map_impacted_assets(text: str, topics: dict) -> list[str]:
    impacted = set()
    lowered = text.lower()
    for alias, symbol in _ASSET_ALIASES.items():
        if alias in lowered:
            impacted.add(symbol)
    for topic in topics:
        impacted.update(_ASSET_RULES.get(topic, []))
    if not impacted:
        impacted.add("XAUUSD")
    return sorted(impacted)


def _impact_level(text: str, topics: dict) -> str:
    lowered = text.lower()
    high_keywords = ["cpi", "fomc", "rate", "nfp", "central bank", "inflation", "jobs report"]
    medium_keywords = ["speech", "minutes", "forecast", "guidance", "trade balance"]
    if any(key in lowered for key in high_keywords):
        return "high"
    if any(key in lowered for key in medium_keywords):
        return "medium"
    if any(topic in topics for topic in ("inflation", "rates", "geopolitics")):
        return "medium"
    return "low"


def _build_rationale(assets: Iterable[str], topics: dict, sentiment_label: str) -> str:
    if "inflation" in topics:
        return (
            "Inflation surprises shift rate expectations, impacting USD strength and real yields, "
            "which typically moves gold and major FX pairs."
        )
    if "rates" in topics:
        return (
            "Interest-rate guidance drives yield differentials, influencing USD crosses and risk appetite."
        )
    if "geopolitics" in topics:
        return (
            "Geopolitical risk can trigger safe-haven demand, supporting gold and pressuring risk assets."
        )
    if "commodities" in topics:
        return "Commodity price moves affect inflation expectations and commodity-linked FX pairs."
    if "growth" in topics:
        return "Growth data shifts risk sentiment and rate expectations, impacting FX majors and indices."
    if "risk" in topics:
        return "Risk sentiment swings drive flows into or out of safe-haven assets like JPY and gold."
    asset_list = ", ".join(assets)
    return f"Market participants may reassess positioning in {asset_list} based on the news tone ({sentiment_label})."
