from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
from sqlalchemy import select

from app.core.config import get_settings
from app.core.rate_limit import allow_run
from app.core.utils import utc_now
from app.db.models import Instrument, MacroEvent, News, SystemHealth, TickOrBar
from app.db.session import SessionLocal
from app.analytics.news_analysis import RuleBasedNewsAnalyzer
from app.ingestion.macro_provider_csv import CsvMacroProvider
from app.ingestion.macro_provider_demo import DemoMacroProvider
from app.ingestion.news_provider_demo import DemoNewsProvider
from app.ingestion.news_provider_rss import RssNewsProvider
from app.ingestion.prices_provider_alphavantage import AlphaVantagePriceProvider
from app.ingestion.prices_provider_demo import DemoPriceProvider
from app.ml.predict import predict_and_store

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _update_health(job_name: str, status: str, error: str | None = None) -> None:
    with SessionLocal() as session:
        row = session.execute(select(SystemHealth).where(SystemHealth.job_name == job_name)).scalar_one_or_none()
        if row:
            row.last_run = utc_now()
            row.status = status
            row.error = error
            row.ok = status == "success"
        else:
            session.add(
                SystemHealth(
                    job_name=job_name,
                    last_run=utc_now(),
                    status=status,
                    error=error,
                    ok=status == "success",
                )
            )
        session.commit()


def _get_price_provider(settings):
    if settings.price_provider == "alphavantage" and settings.alphavantage_api_key:
        return AlphaVantagePriceProvider(settings.alphavantage_api_key)
    return DemoPriceProvider()


def _get_news_provider(settings):
    if settings.news_provider == "rss":
        urls = [url.strip() for url in settings.news_rss_urls.split(",") if url.strip()]
        return RssNewsProvider(urls)
    return DemoNewsProvider()


def _get_macro_provider(settings):
    if settings.macro_provider == "csv":
        return CsvMacroProvider("data/macro_events.csv")
    return DemoMacroProvider()


def ingest_prices() -> None:
    settings = get_settings()
    provider = _get_price_provider(settings)
    try:
        if not allow_run("prices", settings.poll_prices_seconds):
            return
        with SessionLocal() as session:
            instruments = session.execute(select(Instrument)).scalars().all()
            for instrument in instruments:
                last_bar = (
                    session.execute(
                        select(TickOrBar)
                        .where(TickOrBar.instrument_id == instrument.id)
                        .where(TickOrBar.timeframe == "1m")
                        .order_by(TickOrBar.ts.desc())
                        .limit(1)
                    )
                    .scalars()
                    .first()
                )
                start = last_bar.ts if last_bar else None
                bars = provider.fetch_bars(instrument.symbol, "1m", start)
                for bar in bars:
                    exists = (
                        session.query(TickOrBar)
                        .filter(
                            TickOrBar.instrument_id == instrument.id,
                            TickOrBar.timeframe == bar.get("timeframe", "1m"),
                            TickOrBar.ts == bar["ts"],
                        )
                        .first()
                    )
                    if exists:
                        continue
                    session.add(
                        TickOrBar(
                            instrument_id=instrument.id,
                            timeframe=bar.get("timeframe", "1m"),
                            ts=bar["ts"],
                            open=bar["open"],
                            high=bar["high"],
                            low=bar["low"],
                            close=bar["close"],
                            volume=bar.get("volume", 0.0),
                            bid=bar.get("bid"),
                            ask=bar.get("ask"),
                        )
                    )
                session.commit()
                _aggregate_timeframes(session, instrument.id)
        _update_health("prices", "success")
    except Exception as exc:
        logger.exception("Price ingestion failed")
        _update_health("prices", "failed", str(exc))


def ingest_news() -> None:
    settings = get_settings()
    provider = _get_news_provider(settings)
    analyzer = RuleBasedNewsAnalyzer()
    try:
        if not allow_run("news", settings.poll_news_seconds):
            return
        with SessionLocal() as session:
            last_news = session.execute(select(News).order_by(News.published_at.desc()).limit(1)).scalar_one_or_none()
            since = last_news.published_at if last_news else None
            try:
                items = provider.fetch_news(since)
            except Exception:
                logger.exception("Primary news provider failed, falling back to demo feed")
                items = DemoNewsProvider().fetch_news(since)
            for item in items:
                url = item.get("url", "")
                title = item.get("title", "")
                summary = item.get("summary", "")
                analysis = analyzer.analyze(title=title, summary=summary, source=item.get("source", ""))
                exists = session.query(News).filter(News.url == url).first()
                if exists:
                    if exists.title != title or exists.summary != summary:
                        exists.title = title
                        exists.summary = summary
                    exists.analysis_summary = analysis.summary
                    exists.sentiment = analysis.sentiment_score
                    exists.sentiment_label = analysis.sentiment_label
                    exists.impact_level = analysis.impact_level
                    exists.impacted_assets = analysis.impacted_assets
                    exists.rationale = analysis.rationale
                    exists.entities = {"symbols": analysis.impacted_assets}
                    exists.topics = analysis.topics
                    exists.is_fundamental = analysis.is_fundamental
                    continue
                session.add(
                    News(
                        source=item.get("source", "unknown"),
                        published_at=item["published_at"],
                        title=title,
                        summary=summary,
                        analysis_summary=analysis.summary,
                        url=url,
                        sentiment=analysis.sentiment_score,
                        sentiment_label=analysis.sentiment_label,
                        impact_level=analysis.impact_level,
                        impacted_assets=analysis.impacted_assets,
                        rationale=analysis.rationale,
                        entities={"symbols": analysis.impacted_assets},
                        topics=analysis.topics,
                        is_fundamental=analysis.is_fundamental,
                    )
                )
            session.commit()
        _update_health("news", "success")
    except Exception as exc:
        logger.exception("News ingestion failed")
        _update_health("news", "failed", str(exc))


def ingest_macro() -> None:
    settings = get_settings()
    provider = _get_macro_provider(settings)
    try:
        if not allow_run("macro", settings.poll_macro_seconds):
            return
        with SessionLocal() as session:
            last_event = (
                session.execute(select(MacroEvent).order_by(MacroEvent.time.desc()).limit(1))
                .scalars()
                .first()
            )
            since = last_event.time if last_event else None
            events = provider.fetch_events(since)
            for event in events:
                exists = (
                    session.query(MacroEvent)
                    .filter(
                        MacroEvent.time == event["time"],
                        MacroEvent.currency == event.get("currency", "USD"),
                        MacroEvent.name == event.get("name", "Event"),
                        MacroEvent.source == event.get("source", "demo"),
                    )
                    .first()
                )
                if exists:
                    continue
                session.add(
                    MacroEvent(
                        time=event["time"],
                        currency=event.get("currency", "USD"),
                        impact=event.get("impact", "medium"),
                        name=event.get("name", "Event"),
                        forecast=event.get("forecast"),
                        previous=event.get("previous"),
                        actual=event.get("actual"),
                        source=event.get("source", "demo"),
                    )
                )
            session.commit()
        _update_health("macro", "success")
    except Exception as exc:
        logger.exception("Macro ingestion failed")
        _update_health("macro", "failed", str(exc))


def run_prediction() -> None:
    try:
        if not allow_run("predict", get_settings().predict_seconds):
            return
        predict_and_store()
        _update_health("predict", "success")
    except Exception as exc:
        logger.exception("Prediction failed")
        _update_health("predict", "failed", str(exc))


def start_scheduler() -> None:
    settings = get_settings()
    if scheduler.running:
        return
    scheduler.add_job(ingest_prices, "interval", seconds=settings.poll_prices_seconds, id="prices")
    scheduler.add_job(ingest_news, "interval", seconds=settings.poll_news_seconds, id="news")
    scheduler.add_job(ingest_macro, "interval", seconds=settings.poll_macro_seconds, id="macro")
    scheduler.add_job(run_prediction, "interval", seconds=settings.predict_seconds, id="predict")
    scheduler.start()


def _aggregate_timeframes(session, instrument_id: int) -> None:
    rows = (
        session.query(TickOrBar)
        .filter(TickOrBar.instrument_id == instrument_id, TickOrBar.timeframe == "1m")
        .order_by(TickOrBar.ts)
        .all()
    )
    if not rows:
        return
    df = pd.DataFrame(
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
    df = df.set_index("ts")
    for timeframe, rule in {"5m": "5min", "1h": "1H", "1d": "1D"}.items():
        agg = df.resample(rule).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        ).dropna()
        for ts, row in agg.iterrows():
            exists = (
                session.query(TickOrBar)
                .filter(
                    TickOrBar.instrument_id == instrument_id,
                    TickOrBar.timeframe == timeframe,
                    TickOrBar.ts == ts.to_pydatetime(),
                )
                .first()
            )
            if exists:
                continue
            session.add(
                TickOrBar(
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                    ts=ts.to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
        session.commit()
