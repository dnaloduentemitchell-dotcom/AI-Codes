import pandas as pd

from app.features.engineering import compute_features


def test_compute_features_columns():
    data = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=300, freq="min"),
            "open": range(300),
            "high": range(1, 301),
            "low": range(300),
            "close": range(1, 301),
            "volume": range(300),
        }
    )
    feats = compute_features(data)
    assert "ema_20" in feats.columns
    assert "rsi_14" in feats.columns
    assert len(feats) > 0
