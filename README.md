# Forex Intelligence Dashboard (XAU/USD Focus)

A production-ready, Docker Compose-based dashboard for XAU/USD and major FX pairs. It ingests prices, macro events, and news, stores the data in Postgres, runs ML + rule-based analytics, and renders a live Streamlit dashboard. **All signals are probabilistic analytics and are not financial advice.**

## Features
- **Ingestion**: Prices (demo or Alpha Vantage), RSS news, macro events (demo or CSV).
- **Storage**: PostgreSQL with normalized tables for bars, news, macro events, signals, and system health.
- **Analytics**: Regime classification (trend/range/volatile), probabilistic bull/bear/neutral signal.
- **ML**: Logistic regression with calibration and walk-forward split.
- **Dashboard**: Streamlit UI with live tickers, charts, and panels.
- **Resilience**: Retries, rate limiting, and graceful fallback to demo mode.

## Quickstart
1. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
2. Start the stack:
   ```bash
   docker compose up --build
   ```
3. Visit the dashboard:
   - Streamlit: http://localhost:8501
   - API docs: http://localhost:8000/docs

## Database Setup (Docker Compose)
The Docker Compose stack includes PostgreSQL and initializes it with default credentials.

**Default DB settings**
- Host: `db` (inside Docker) or `localhost` (from your machine)
- Port: `5432`
- Database: `forex`
- User: `postgres`
- Password: `postgres`

**Common Windows setup steps**
1. Ensure Docker Desktop is running.
2. Copy `.env.example` to `.env`, then verify `DATABASE_URL` points to the Docker database:
   ```bash
   DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/forex
   ```
3. Start the stack:
   ```bash
   docker compose up --build
   ```
4. If you are running the API **outside** Docker (Windows host Python), update `DATABASE_URL` to use `localhost`:
   ```bash
   DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/forex
   ```

**Troubleshooting DB errors**
- If you see connection errors, ensure the `db` container is healthy:
  ```bash
  docker compose ps
  ```
- If port 5432 is already in use, change the exposed port in `docker-compose.yml`:
  ```yaml
  ports:
    - "5433:5432"
  ```
  Then set `DATABASE_URL` to use port `5433`.

## Demo Mode
If no API keys are provided, the system uses CSV demo data from `data/` to run end-to-end.

## Running Locally (without Docker)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/forex
export REDIS_URL=redis://localhost:6379/0
uvicorn app.main:app --reload
```
Then run the dashboard:
```bash
streamlit run dashboard/app.py
```

## Adding a New Provider Adapter
1. Implement a new class in `app/ingestion/` that extends `PriceProvider`, `NewsProvider`, or `MacroProvider`.
2. Wire it into `app/services/scheduler.py` inside the `_get_*_provider` helpers.
3. Expose any keys or settings in `app/core/config.py` and document them in `.env.example`.

## API Endpoints
- `GET /health`
- `GET /prices?instrument_id=1&timeframe=1m&limit=300`
- `GET /news?limit=50`
- `GET /macro?limit=100`
- `GET /signals?limit=50`

## Smoke Test
```bash
./scripts/smoke_test.sh
```

## Disclaimer
This project provides **probabilistic analytics only**. It is not trading advice, and it does not guarantee outcomes.
