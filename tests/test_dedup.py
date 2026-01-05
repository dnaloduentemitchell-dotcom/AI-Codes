import importlib
import os
import tempfile
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError


def test_bar_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_url = f"sqlite+pysqlite:///{tmpdir}/test.db"
        os.environ["DATABASE_URL"] = db_url
        import app.core.config as config

        importlib.reload(config)
        import app.db.session as session
        importlib.reload(session)
        import app.db.models as models
        import app.db.init_db as init_db

        init_db.init_db()
        with session.SessionLocal() as db:
            instrument = db.query(models.Instrument).first()
            ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
            bar = models.TickOrBar(
                instrument_id=instrument.id,
                timeframe="1m",
                ts=ts,
                open=1,
                high=1,
                low=1,
                close=1,
                volume=1,
            )
            db.add(bar)
            db.commit()
            dup = models.TickOrBar(
                instrument_id=instrument.id,
                timeframe="1m",
                ts=ts,
                open=1,
                high=1,
                low=1,
                close=1,
                volume=1,
            )
            db.add(dup)
            with pytest.raises(IntegrityError):
                db.commit()
