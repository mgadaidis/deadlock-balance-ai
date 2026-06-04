# Backend — Deadlock Game-Balance AI

FastAPI service that pulls match analytics from the public [Deadlock API](https://deadlock-api.com/), processes it with pandas + scikit-learn, and serves balance verdicts to the React dashboard.

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API is now at http://127.0.0.1:8000 — open `/docs` for Swagger UI.

## First run

The DB is empty when you start. Populate it once with:

```bash
curl -X POST http://127.0.0.1:8000/refresh
```

…or, equivalently, from the CLI:

```bash
python scripts/fetch_data.py
```

## Module map

| File | Role |
| ---- | ---- |
| `app/main.py` | FastAPI app, CORS, lifespan, refresh endpoint |
| `app/config.py` | Settings loaded from `.env` |
| `app/database.py` | SQLAlchemy engine, session, `Base`, `get_db` |
| `app/models.py` | ORM tables: `Hero`, `HeroStat`, `BalanceFlag` |
| `app/schemas.py` | Pydantic response/request schemas |
| `app/deadlock_client.py` | Async HTTP client for the Deadlock API |
| `app/data_pipeline.py` | Fetch → normalise (pandas) → persist → analyse |
| `app/ml/balance_analyzer.py` | Threshold + IsolationForest balance verdicts |
| `app/ml/predictor.py` | Logistic win-probability predictor |
| `app/routers/heroes.py` | `/heroes`, `/heroes/stats`, `/heroes/{id}/stats` |
| `app/routers/balance.py` | `/balance/flags`, `/balance/summary` |
| `app/routers/predict.py` | `POST /predict` |
| `scripts/fetch_data.py` | CLI wrapper around the pipeline |

## Environment

See `.env.example` for the full list. Most important:

* `DEADLOCK_API_BASE` — upstream analytics host
* `DATABASE_URL` — SQLite by default; swap for Postgres in production
* `WINRATE_LOW` / `WINRATE_HIGH` — the "balanced" band
