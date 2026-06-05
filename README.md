# Deadlock Game-Balance AI

A data-driven balance-analysis system for Valve's **Deadlock**. The system
fetches public match analytics from [deadlock-api.com](https://deadlock-api.com/),
computes per-hero performance metrics, surfaces overpowered and underpowered
heroes with explainable rationales, and predicts team win probability.

> Project — authors: **Mia Giorgadze, Mikheil Gadaidis**.

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
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ React 18 + Vite frontend                                                │
  │  • Recharts visualisations                                              │
  │  • Pages: Overview, Simulator, Hero Recommendation, Item Recommendation |
  └─────────────────────────────────────────────────────────────────────────┘
```

This matches Section 3.6 of the proposal exactly.

---

### Prerequisites

Before running the project, make sure the device has the following installed:

- Python 3.10 or newer
- Node.js and npm
- Git, if cloning from GitHub

Python is required to run the FastAPI backend. Node.js and npm are required to run the React frontend.

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

## Endpoints

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
```
deadlock-balance-ai/
├── backend/                 FastAPI backend, data pipeline, ML models, SQLite cache
│   ├── app/                 Main backend application code
│   │   ├── data/            Item upgrade paths, archetypes, and data format files
│   │   ├── ml/              Balance analyzer, simulator, Random Forest ML model
│   │   └── routers/         API routes for heroes, balance, items, and prediction
│   ├── scripts/             Optional data-fetching scripts
│   ├── requirements.txt     Python dependencies
│   └── .env.example         Example backend environment configuration
│
├── frontend/                React + Vite frontend
│   ├── src/                 Main frontend source code
│   │   ├── api/             Axios API client
│   │   ├── components/      Reusable UI and chart components
│   │   ├── contexts/        Shared item data context
│   │   ├── pages/           Overview, Simulator, Hero Recs, Item Recs, Heroes
│   │   └── theme/           Frontend color/theme helpers
│   ├── package.json         Frontend dependencies and scripts
│   └── vite.config.js       Vite configuration and backend proxy
│
├── docs/                    Project documentation and evidence
│   ├── ML_MODEL.md          Machine learning model explanation
│   ├── API_ENDPOINTS.md     Backend API endpoint documentation
│   ├── DATA_PIPELINE.md     Data collection and preprocessing explanation
│   ├── USER_GUIDE.md        User guide for the final app
│   └── screenshots/         App and endpoint screenshots
│
├── TEAMWORK.md              Role distribution and collaboration strategy
├── TESTING.md               Manual and automated testing checklist
├── .gitignore               Ignored local/cache/build files
├── LICENSE                  MIT license
├── run-dev.sh               Optional helper script for running the app
└── README.md                Main project overview and setup guide
```

```

See `backend/README.md` and `frontend/README.md` for module-level detail.

---

## Scope

In scope: hero-level analysis, win rate / pick rate / KDA /
damage, overpowered-vs-underpowered detection, win-probability prediction, a
React dashboard.

Out of scope: deep learning, live match tracking, simulation of game mechanics.

---

## License

MIT — see `LICENSE`. Data: `deadlock-api.com`. Not affiliated with Valve.
