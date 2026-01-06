from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components

API_URL = os.getenv("API_URL", "http://api:8000")

st.set_page_config(page_title="NewsTracker", layout="wide")

st.markdown(
    """
    <style>
    html, body, [class*="st-"] {
        background-color: #0b0f17;
        color: #e6edf3;
    }
    .news-card {
        border: 1px solid #1f2a36;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 12px;
        background: #101826;
    }
    .impact-high { color: #ff6b6b; font-weight: 600; }
    .impact-medium { color: #f7b731; font-weight: 600; }
    .impact-low { color: #20bf6b; font-weight: 600; }
    .sentiment-bullish { color: #2ecc71; }
    .sentiment-bearish { color: #e74c3c; }
    .sentiment-neutral { color: #95a5a6; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("NewsTracker: Real-Time Forex News Intelligence")
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


instruments = fetch_json("/instruments")
instrument_symbols = [item["symbol"] for item in instruments]
instrument_map = {item["symbol"]: item["id"] for item in instruments}

with st.sidebar:
    st.header("Filters")
    instrument = st.selectbox("Instrument", instrument_symbols, index=0)
    limit = st.slider("Rows", 50, 500, 200)
    timeframe = st.selectbox("Timeframe", ["1m", "5m", "1h", "1d"], index=0)
    impact_filter = st.selectbox("Impact level", ["all", "high", "medium", "low"], index=0)
    sentiment_filter = st.selectbox("Sentiment", ["all", "bullish", "bearish", "neutral"], index=0)
    fundamental_only = st.toggle("Fundamental only", value=True)
    search_query = st.text_input("Search")

prices = fetch_json(
    "/prices",
    {"instrument_id": instrument_map.get(instrument, 1), "timeframe": timeframe, "limit": limit},
)
news_params = {
    "limit": 200,
    "instrument": instrument,
    "fundamental_only": fundamental_only,
}
if impact_filter != "all":
    news_params["impact"] = impact_filter
if sentiment_filter != "all":
    news_params["sentiment"] = sentiment_filter
if search_query:
    news_params["q"] = search_query
news = fetch_json("/news", news_params)
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

st.subheader("Live News Feed (Streaming)")
components.html(
    f"""
    <div id="news-feed" style="max-height: 420px; overflow-y: auto;"></div>
    <script>
    const feed = document.getElementById("news-feed");
    const source = new EventSource("{API_URL}/news/stream?instrument={instrument}");
    function renderCard(item) {{
        const card = document.createElement("div");
        card.className = "news-card";
        const impactClass = `impact-${{item.impact_level}}`;
        const sentimentClass = `sentiment-${{item.sentiment_label}}`;
        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div><strong>${{item.title}}</strong></div>
                <div class="${{impactClass}}">${{item.impact_level.toUpperCase()}}</div>
            </div>
            <div style="font-size:12px; opacity:0.8;">${{new Date(item.published_at).toUTCString()}} · ${item.source}</div>
            <div style="margin:6px 0;">${{item.analysis_summary || item.summary}}</div>
            <div style="font-size:12px;">Assets: ${item.impacted_assets?.join(", ") || ""}</div>
            <div style="font-size:12px;" class="${{sentimentClass}}">Sentiment: ${item.sentiment_label}</div>
            <div style="font-size:12px; opacity:0.8;">Why: ${item.rationale || ""}</div>
        `;
        feed.prepend(card);
    }}
    source.onmessage = (event) => {{
        const data = JSON.parse(event.data);
        data.forEach(renderCard);
    }};
    </script>
    """,
    height=460,
)

if prices:
    df = pd.DataFrame(prices)
    df["ts"] = pd.to_datetime(df["ts"])
    df["rsi_14"] = _rsi(df["close"], 14)
    df["macd"] = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    st.subheader(f"{instrument} Price Chart with News")
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["ts"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name=instrument,
            )
        ]
    )
    if news:
        news_df = pd.DataFrame(news)
        news_df["published_at"] = pd.to_datetime(news_df["published_at"])
        fig.add_trace(
            go.Scatter(
                x=news_df["published_at"],
                y=[df["close"].iloc[-1]] * len(news_df),
                mode="markers",
                marker=dict(size=6, color="#f7b731"),
                name="News",
                text=news_df["title"],
                hovertemplate="%{text}<extra></extra>",
            )
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

    if news:
        news_df = pd.DataFrame(news)
        news_df["published_at"] = pd.to_datetime(news_df["published_at"])
        df = df.sort_values("ts")
        df["return_5"] = df["close"].pct_change(5)
        merged = pd.merge_asof(
            news_df.sort_values("published_at"),
            df[["ts", "return_5"]].rename(columns={"ts": "published_at"}),
            on="published_at",
        )
        merged = merged.dropna()
        if not merged.empty:
            corr = merged["return_5"].corr(merged["sentiment"].astype(float))
            st.metric("News/Price Correlation (5 bars)", f"{corr:.2f}")

st.subheader("Latest News")
for item in news[:20]:
    local_time = datetime.fromisoformat(str(item["published_at"]).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f"- **{local_time}** · {item['title']} ([link]({item['url']}))  "
        f"  \n  Impact: `{item['impact_level']}` · Sentiment: `{item['sentiment_label']}`"
    )

st.subheader("Macro Events")
if macro:
    st.dataframe(pd.DataFrame(macro))
