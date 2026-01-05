from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select

from app.analytics.regime import classify_regime
from app.analytics.signals import build_confidence, confidence_reason, label_from_probability
from app.core.config import get_settings
from app.core.utils import utc_now
from app.db.models import Instrument, MacroEvent, News, Signal, TickOrBar
from app.db.session import SessionLocal
from app.features.engineering import add_macro_features, add_news_features, compute_features
from app.ml.explain import build_explanation


def latest_model() -> tuple[str, dict] | None:
    settings = get_settings()
    model_dir = Path(settings.model_dir)
    if not model_dir.exists():
        return None
    models = sorted(model_dir.glob("*.joblib"))
    if not models:
        return None
    latest = models[-1]
    payload = joblib.load(latest)
    return latest.stem, payload


def predict_and_store() -> dict:
    model_info = latest_model()
    if not model_info:
        return {"status": "no_model"}
    model_version, payload = model_info
    model = payload["model"]
    feature_cols = payload["features"]
    with SessionLocal() as session:
        instrument = session.execute(select(Instrument).where(Instrument.symbol == "XAUUSD")).scalar_one()
        rows = (
            session.query(TickOrBar)
            .filter(TickOrBar.instrument_id == instrument.id, TickOrBar.timeframe == "1m")
            .order_by(TickOrBar.ts)
            .all()
        )
        news_rows = session.query(News).order_by(News.published_at).all()
        macro_rows = session.query(MacroEvent).order_by(MacroEvent.time).all()
        if len(rows) < 250:
            return {"status": "insufficient_data"}
        data = pd.DataFrame(
            [
                {
                    "ts": row.ts,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": row.volume,
                }
                for row in rows
            ]
        )
        feats = compute_features(data)
        news_df = pd.DataFrame(
            [
                {"published_at": row.published_at, "sentiment": row.sentiment or 0.0}
                for row in news_rows
            ]
        )
        macro_df = pd.DataFrame(
            [
                {"time": row.time, "currency": row.currency, "impact": row.impact}
                for row in macro_rows
            ]
        )
        feats = add_news_features(feats, news_df)
        feats = add_macro_features(feats, macro_df)
        latest = feats.iloc[-1:]
        probs = model.predict_proba(latest[feature_cols])[0]
        classes = model.classes_
        probabilities = {cls: float(prob) for cls, prob in zip(classes, probs)}
        prob_bull = probabilities.get("Bullish", 0.0)
        prob_bear = probabilities.get("Bearish", 0.0)
        label = label_from_probability(prob_bull, prob_bear)
        confidence = build_confidence(probabilities)
        regime = classify_regime(feats)
        explanation = build_explanation(latest.iloc[-1], probabilities, regime)
        explanation["confidence_reason"] = confidence_reason(
            regime["regime"], explanation.get("sentiment_score", 0.0), regime["evidence"].get("volatility_percentile", 0.0)
        )
        signal = Signal(
            instrument_id=instrument.id,
            ts=utc_now(),
            label=label,
            confidence=confidence,
            explanation_json=explanation,
            model_version=model_version,
        )
        session.add(signal)
        session.commit()
    return {"status": "ok", "label": label, "confidence": confidence}


if __name__ == "__main__":
    print(predict_and_store())
