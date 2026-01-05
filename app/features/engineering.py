from __future__ import annotations

import numpy as np
import pandas as pd


def compute_features(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy().sort_values("ts")
    returns = df["close"].pct_change()
    df["log_return_1"] = np.log1p(returns)
    df["log_return_5"] = df["close"].pct_change(5)
    df["log_return_60"] = df["close"].pct_change(60)
    df["volatility_20"] = returns.rolling(20).std()
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["rsi_14"] = _rsi(df["close"], 14)
    df["macd"] = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["atr_14"] = _atr(df, 14)
    df = df.dropna()
    return df


def add_news_features(features_df: pd.DataFrame, news_df: pd.DataFrame) -> pd.DataFrame:
    df = features_df.copy()
    if news_df.empty:
        df["news_sentiment_24h"] = 0.0
        return df
    news_df = news_df.sort_values("published_at")
    def sentiment_window(ts: pd.Timestamp) -> float:
        window = news_df[(news_df["published_at"] <= ts) & (news_df["published_at"] >= ts - pd.Timedelta(hours=24))]
        return float(window["sentiment"].mean()) if not window.empty else 0.0
    df["news_sentiment_24h"] = df["ts"].apply(sentiment_window)
    return df


def add_macro_features(features_df: pd.DataFrame, macro_df: pd.DataFrame) -> pd.DataFrame:
    df = features_df.copy()
    if macro_df.empty:
        df["minutes_to_high_impact_usd"] = 0.0
        return df
    macro_df = macro_df.sort_values("time")
    high_impact = macro_df[(macro_df["currency"] == "USD") & (macro_df["impact"] == "high")]
    def minutes_to_next(ts: pd.Timestamp) -> float:
        future = high_impact[high_impact["time"] >= ts]
        if future.empty:
            return 0.0
        return float((future.iloc[0]["time"] - ts).total_seconds() / 60)
    df["minutes_to_high_impact_usd"] = df["ts"].apply(minutes_to_next)
    return df


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()
