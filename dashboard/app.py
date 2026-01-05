from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://api:8000")

st.set_page_config(page_title="Forex Intelligence Dashboard", layout="wide")

st.title("Forex Intelligence Dashboard - XAU/USD Focus")
st.caption("Signals are probabilistic analytics, not financial advice.")


def fetch_json(path: str, params: dict | None = None):
    response = requests.get(f"{API_URL}{path}", params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


with st.sidebar:
    st.header("Filters")
    limit = st.slider("Rows", 50, 500, 200)
    timeframe = st.selectbox("Timeframe", ["1m", "5m", "1h", "1d"], index=0)
    news_source_filter = st.text_input("News source filter (optional)")
    impact_filter = st.selectbox("Macro impact", ["all", "high", "medium", "low"], index=0)

prices = fetch_json("/prices", {"instrument_id": 1, "timeframe": timeframe, "limit": limit})
news = fetch_json("/news", {"limit": 50})
macro = fetch_json("/macro", {"limit": 50})
signals = fetch_json("/signals", {"limit": 5})

st.subheader("Live Ticker")
columns = st.columns(4)
with columns[0]:
    st.markdown("**Latest Price**")
    if prices:
        st.write(f"{prices[-1]['close']:.2f}")
with columns[1]:
    st.markdown("**Latest Signal**")
    if signals:
        latest_signal = signals[0]
        st.write(f"{latest_signal['label']} ({latest_signal['confidence']:.2f})")
with columns[2]:
    st.markdown("**Latest News**")
    if news:
        st.write(news[0]["title"])
with columns[3]:
    st.markdown("**Next Macro Event**")
    if macro:
        st.write(macro[0]["name"])

st.divider()

if prices:
    df = pd.DataFrame(prices)
    df["ts"] = pd.to_datetime(df["ts"])
    df["rsi_14"] = _rsi(df["close"], 14)
    df["macd"] = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    st.subheader("XAU/USD Candlestick")
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["ts"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="XAU/USD",
            )
        ]
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("RSI & MACD")
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(x=df["ts"], y=df["rsi_14"], name="RSI 14"))
    rsi_fig.update_layout(yaxis_title="RSI")
    st.plotly_chart(rsi_fig, use_container_width=True)

    macd_fig = go.Figure()
    macd_fig.add_trace(go.Scatter(x=df["ts"], y=df["macd"], name="MACD"))
    macd_fig.add_trace(go.Scatter(x=df["ts"], y=df["macd_signal"], name="Signal"))
    st.plotly_chart(macd_fig, use_container_width=True)

st.subheader("Signal Details")
if signals:
    st.json(signals[0])
    if len(signals) > 1:
        prev = signals[1]
        st.markdown("**What changed**")
        st.write(
            f"Previous: {prev['label']} ({prev['confidence']:.2f}) → "
            f"Current: {signals[0]['label']} ({signals[0]['confidence']:.2f})"
        )
    regime = signals[0].get("explanation", {}).get("regime", {})
    if regime:
        st.markdown(f"**Regime:** {regime.get('regime', 'unknown')}")

st.subheader("Sentiment Over Time")
if news:
    news_df = pd.DataFrame(news)
    news_df["published_at"] = pd.to_datetime(news_df["published_at"])
    sentiment_fig = go.Figure()
    sentiment_fig.add_trace(
        go.Scatter(x=news_df["published_at"], y=news_df["sentiment"], mode="lines+markers")
    )
    st.plotly_chart(sentiment_fig, use_container_width=True)

st.subheader("Latest News")
filtered_news = news
if news_source_filter:
    filtered_news = [item for item in filtered_news if news_source_filter.lower() in item["source"].lower()]
for item in filtered_news[:20]:
    st.markdown(f"- [{item['title']}]({item['url']}) ({item['source']})")

st.subheader("Macro Events")
filtered_macro = macro
if impact_filter != "all":
    filtered_macro = [item for item in filtered_macro if item["impact"] == impact_filter]
if filtered_macro:
    st.dataframe(pd.DataFrame(filtered_macro))
