from sqlalchemy import select

from app.db.models import Base, Instrument
from app.db.session import engine, SessionLocal


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        existing = session.execute(
            select(Instrument).where(Instrument.symbol == "XAUUSD")
        ).scalar_one_or_none()
        if not existing:
            session.add(Instrument(symbol="XAUUSD", type="metal", pip_value=0.01))
            session.add(Instrument(symbol="EURUSD", type="fx", pip_value=0.0001))
            session.add(Instrument(symbol="GBPUSD", type="fx", pip_value=0.0001))
            session.add(Instrument(symbol="USDJPY", type="fx", pip_value=0.01))
            session.add(Instrument(symbol="AUDUSD", type="fx", pip_value=0.0001))
            session.add(Instrument(symbol="USDCAD", type="fx", pip_value=0.0001))
            session.commit()
