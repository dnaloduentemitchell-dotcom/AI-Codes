from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(32))
    pip_value: Mapped[float] = mapped_column(Float, default=0.0)

    bars: Mapped[list[TickOrBar]] = relationship("TickOrBar", back_populates="instrument")


class TickOrBar(Base):
    __tablename__ = "ticks_or_bars"
    __table_args__ = (
        UniqueConstraint("instrument_id", "timeframe", "ts", name="uq_bar"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"))
    timeframe: Mapped[str] = mapped_column(String(16))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask: Mapped[float | None] = mapped_column(Float, nullable=True)

    instrument: Mapped[Instrument] = relationship("Instrument", back_populates="bars")


class News(Base):
    __tablename__ = "news"
    __table_args__ = (UniqueConstraint("url", name="uq_news_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(128))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str] = mapped_column(String(2048), default="")
    url: Mapped[str] = mapped_column(String(1024))
    sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)
    entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    topics: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class MacroEvent(Base):
    __tablename__ = "macro_events"
    __table_args__ = (
        UniqueConstraint("time", "currency", "name", "source", name="uq_macro"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    currency: Mapped[str] = mapped_column(String(8))
    impact: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(256))
    forecast: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(128))


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("instrument_id", "ts", "model_version", name="uq_signal"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    label: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    explanation_json: Mapped[dict] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String(64))


class SystemHealth(Base):
    __tablename__ = "system_health"
    __table_args__ = (UniqueConstraint("job_name", name="uq_health_job"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(64))
    last_run: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
