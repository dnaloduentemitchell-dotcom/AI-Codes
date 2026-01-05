from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import get_redis
from app.core.config import get_settings
from app.db.models import MacroEvent, News, Signal, SystemHealth, TickOrBar
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
def news(limit: int = 50, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = (
        db.execute(select(News).order_by(News.published_at.desc()).limit(limit))
        .scalars()
        .all()
    )
    return [
        {
            "published_at": row.published_at,
            "source": row.source,
            "title": row.title,
            "summary": row.summary,
            "url": row.url,
            "sentiment": row.sentiment,
        }
        for row in rows
    ]


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
