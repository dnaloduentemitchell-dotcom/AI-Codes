import importlib
import os
import tempfile
from datetime import datetime, timedelta, timezone


def test_training_pipeline_runs():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_url = f"sqlite+pysqlite:///{tmpdir}/train.db"
        os.environ["DATABASE_URL"] = db_url
        os.environ["MODEL_DIR"] = f"{tmpdir}/models"
        import app.core.config as config

        importlib.reload(config)
        import app.db.session as session
        importlib.reload(session)
        import app.db.models as models
        import app.db.init_db as init_db
        import app.ml.train as train

        init_db.init_db()
        with session.SessionLocal() as db:
            instrument = db.query(models.Instrument).first()
            start = datetime(2024, 1, 1, tzinfo=timezone.utc)
            for i in range(400):
                ts = start + timedelta(minutes=i)
                db.add(
                    models.TickOrBar(
                        instrument_id=instrument.id,
                        timeframe="1m",
                        ts=ts,
                        open=2000 + i * 0.1,
                        high=2000 + i * 0.1 + 0.2,
                        low=2000 + i * 0.1 - 0.2,
                        close=2000 + i * 0.1 + 0.05,
                        volume=1000 + i,
                    )
                )
            db.commit()
        result = train.train_model()
        assert result["status"] in {"trained", "no_data"}
