# Deadlock Game-Balance AI

A data-driven balance-analysis system for Valve's **Deadlock**. The system
fetches public match analytics from [deadlock-api.com](https://deadlock-api.com/),
computes per-hero performance metrics, surfaces overpowered and underpowered
heroes with explainable rationales, and predicts team win probability.

> Midterm project — authors: **Mia Giorgadze, Mikheil Gadaidis**.

---

## Architecture

```
  ┌──────────────────────┐
  │ deadlock-api.com     │  (public analytics for Valve's Deadlock)
  └──────────┬───────────┘
             │ HTTPS (httpx, async)
             ▼
  ┌──────────────────────────────────────────────┐
  │ FastAPI backend (Python 3.10+)               │
  │  • httpx client → pandas normalisation       │
  │  • SQLAlchemy ORM → SQLite                   │
  │  • scikit-learn (IsolationForest) analyser   │
  │  • REST endpoints: /heroes, /balance, …      │
  └──────────┬───────────────────────────────────┘
             │ JSON, /api/* (CORS, axios)
             ▼
  ┌──────────────────────────────────────────────┐
  │ React 18 + Vite frontend                     │
  │  • Recharts visualisations                   │
  │  • Pages: Dashboard, Heroes, Balance, Predict│
  └──────────────────────────────────────────────┘
```

This matches Section 3.6 of the proposal exactly.

---

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API is now at <http://127.0.0.1:8000>. Open `/docs` for the auto-generated Swagger UI.

### 2. Frontend (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>.

### 3. First data load

On the Dashboard, click **Refresh data**. This calls `POST /refresh`, which
pulls heroes and aggregated stats from the Deadlock API, normalises them,
stores them in `backend/deadlock.db`, and runs the balance analyser.

---

## Endpoints (cheat-sheet)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/refresh` | Pull fresh data and re-run analysis |
| `GET`  | `/heroes` | Static hero metadata |
| `GET`  | `/heroes/stats` | Latest snapshot per hero |
| `GET`  | `/heroes/{id}/stats` | Time series for one hero |
| `GET`  | `/balance/flags` | Verdicts, rationales, recommendations |
| `GET`  | `/balance/summary` | Counts per verdict |
| `POST` | `/predict` | Win-probability for a team |
| `GET`  | `/health` | Liveness probe |

---

## Repository layout

```
deadlock-balance-ai/
├── backend/        FastAPI + pandas + scikit-learn + SQLite
├── frontend/       React + Vite + Recharts + axios
├── .gitignore
├── LICENSE         MIT
└── README.md       (this file)
```

See `backend/README.md` and `frontend/README.md` for module-level detail.

---

## Scope

In scope (per the proposal): hero-level analysis, win rate / pick rate / KDA /
damage, overpowered-vs-underpowered detection, win-probability prediction, a
React dashboard.

Out of scope: deep learning, live match tracking, item-level recommendations
(may be added later as data permits), simulation of game mechanics.

---

## License

MIT — see `LICENSE`. Data: `deadlock-api.com`. Not affiliated with Valve.
