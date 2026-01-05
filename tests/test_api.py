import importlib
import os
import tempfile
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_health_endpoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_url = f"sqlite+pysqlite:///{tmpdir}/test.db"
        os.environ["DATABASE_URL"] = db_url
        import app.core.config as config

        importlib.reload(config)
        import app.db.session as session
        importlib.reload(session)
        import app.db.models as models
        import app.db.init_db as init_db
        import app.api.routes as routes

        init_db.init_db()
        with session.SessionLocal() as db:
            db.add(
                models.SystemHealth(
                    job_name="prices",
                    last_run=datetime.now(timezone.utc),
                    status="success",
                    error=None,
                    ok=True,
                )
            )
            db.commit()
        app = FastAPI()
        app.include_router(routes.router)
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["jobs"][0]["job_name"] == "prices"
