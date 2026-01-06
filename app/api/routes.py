from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import get_redis
from app.core.config import get_settings
from app.db.models import Instrument, MacroEvent, News, Signal, SystemHealth, TickOrBar
from app.db.session import SessionLocal

router = APIRouter()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, Any]:
    settings = get_settings()
    redis_ok = False
    client = get_redis()
    if client is not None:
        try:
            redis_ok = bool(client.ping())
        except Exception:
            redis_ok = False
    health_rows = db.execute(select(SystemHealth)).scalars().all()
    return {
        "status": "ok",
        "environment": settings.environment,
        "redis_ok": redis_ok,
        "jobs": [
            {
                "job_name": row.job_name,
                "last_run": row.last_run,
                "status": row.status,
                "error": row.error,
            }
            for row in health_rows
        ],
    }


@router.get("/prices")
def prices(
    instrument_id: int,
    timeframe: str = "1h",
    limit: int = 300,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            select(TickOrBar)
            .where(TickOrBar.instrument_id == instrument_id)
            .where(TickOrBar.timeframe == timeframe)
            .order_by(TickOrBar.ts.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        {
            "ts": row.ts,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume,
        }
        for row in rows
    ][::-1]


@router.get("/news")
def news(
    limit: int = 50,
    instrument: str | None = None,
    impact: str | None = None,
    sentiment: str | None = None,
    q: str | None = None,
    fundamental_only: bool = False,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = (
        db.execute(select(News).order_by(News.published_at.desc()).limit(limit))
        .scalars()
        .all()
    )
    filtered = []
    for row in rows:
        if instrument and instrument not in (row.impacted_assets or []):
            continue
        if impact and row.impact_level != impact:
            continue
        if sentiment and row.sentiment_label != sentiment:
            continue
        if fundamental_only and not row.is_fundamental:
            continue
        if q:
            haystack = f"{row.title} {row.summary} {row.analysis_summary}".lower()
            if q.lower() not in haystack:
                continue
        filtered.append(row)
    return [_serialize_news(row) for row in filtered]


@router.get("/news/stream")
async def news_stream(request: Request, instrument: str | None = None) -> StreamingResponse:
    async def event_generator():
        last_seen: datetime | None = None
        while True:
            if await request.is_disconnected():
                break
            with SessionLocal() as session:
                query = select(News).order_by(News.published_at.desc()).limit(25)
                if last_seen is not None:
                    query = select(News).where(News.published_at > last_seen).order_by(News.published_at.desc())
                rows = session.execute(query).scalars().all()
                if instrument:
                    rows = [row for row in rows if instrument in (row.impacted_assets or [])]
                if rows:
                    last_seen = max(row.published_at for row in rows)
                    payload = json.dumps([_serialize_news(row) for row in rows], default=str)
                    yield f"data: {payload}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/macro")
def macro_events(
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    query = select(MacroEvent)
    if start:
        query = query.where(MacroEvent.time >= start)
    if end:
        query = query.where(MacroEvent.time <= end)
    rows = db.execute(query.order_by(MacroEvent.time.desc()).limit(limit)).scalars().all()
    return [
        {
            "time": row.time,
            "currency": row.currency,
            "impact": row.impact,
            "name": row.name,
            "forecast": row.forecast,
            "previous": row.previous,
            "actual": row.actual,
            "source": row.source,
        }
        for row in rows
    ]


@router.get("/signals")
def signals(limit: int = 50, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(select(Signal).order_by(Signal.ts.desc()).limit(limit)).scalars().all()
    return [
        {
            "ts": row.ts,
            "label": row.label,
            "confidence": row.confidence,
            "explanation": row.explanation_json,
            "model_version": row.model_version,
        }
        for row in rows
    ]


@router.get("/instruments")
def instruments(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(select(Instrument).order_by(Instrument.symbol)).scalars().all()
    return [
        {
            "id": row.id,
            "symbol": row.symbol,
            "type": row.type,
            "pip_value": row.pip_value,
        }
        for row in rows
    ]


def _serialize_news(row: News) -> dict[str, Any]:
    return {
        "id": row.id,
        "published_at": row.published_at,
        "source": row.source,
        "title": row.title,
        "summary": row.summary,
        "analysis_summary": row.analysis_summary,
        "url": row.url,
        "sentiment": row.sentiment,
        "sentiment_label": row.sentiment_label,
        "impact_level": row.impact_level,
        "impacted_assets": row.impacted_assets,
        "rationale": row.rationale,
        "topics": row.topics,
        "is_fundamental": row.is_fundamental,
    }
