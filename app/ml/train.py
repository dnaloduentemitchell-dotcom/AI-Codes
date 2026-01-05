from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

from app.core.config import get_settings
from app.db.models import MacroEvent, News, TickOrBar
from app.db.session import SessionLocal
from app.features.engineering import add_macro_features, add_news_features, compute_features


def train_model() -> dict:
    settings = get_settings()
    with SessionLocal() as session:
        rows = session.query(TickOrBar).filter(TickOrBar.timeframe == "1m").order_by(TickOrBar.ts).all()
        news_rows = session.query(News).order_by(News.published_at).all()
        macro_rows = session.query(MacroEvent).order_by(MacroEvent.time).all()
    if not rows:
        return {"status": "no_data"}
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
    horizon = settings.signal_horizon_minutes
    feats["future_return"] = feats["close"].pct_change(periods=horizon).shift(-horizon)
    feats = feats.dropna()
    threshold = feats["future_return"].std() * 0.5
    feats["label"] = np.where(
        feats["future_return"] > threshold,
        "Bullish",
        np.where(feats["future_return"] < -threshold, "Bearish", "Neutral"),
    )
    feature_cols = [
        "log_return_1",
        "log_return_5",
        "log_return_60",
        "volatility_20",
        "ema_20",
        "ema_50",
        "ema_200",
        "rsi_14",
        "macd",
        "macd_signal",
        "atr_14",
        "news_sentiment_24h",
        "minutes_to_high_impact_usd",
    ]
    X = feats[feature_cols]
    y = feats["label"]
    split_idx = int(len(feats) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    base = LogisticRegression(max_iter=200)
    calibrated = CalibratedClassifierCV(base, cv=3)
    calibrated.fit(X_train, y_train)
    preds = calibrated.predict(X_test)
    report = classification_report(y_test, preds, output_dict=True)
    model_dir = Path(settings.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    model_version = f"lr_{pd.Timestamp.utcnow().strftime('%Y%m%d%H%M%S')}"
    model_path = model_dir / f"{model_version}.joblib"
    joblib.dump({"model": calibrated, "features": feature_cols}, model_path)
    return {"status": "trained", "model_version": model_version, "report": report}


if __name__ == "__main__":
    print(train_model())
