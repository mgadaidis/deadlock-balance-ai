# Frontend — Deadlock Game-Balance AI

Vite + React 18 dashboard for the FastAPI backend.

## Quick start

```bash
cd frontend
npm install        # or: pnpm install
npm run dev
```

Open http://127.0.0.1:5173 and click **Refresh data** on the Dashboard the
first time you run it.

## Configuration

Requests go to `/api/*`, which the Vite dev server proxies to
`http://127.0.0.1:8000` (the backend). To point at a different backend, edit
the `proxy` block in `vite.config.js`, or change `baseURL` in
`src/api/client.js` for a production build.

## Pages

| Route | Component | Purpose |
| ----- | --------- | ------- |
| `/`         | `pages/Dashboard.jsx` | Top-level tiles, refresh button, win-rate bar chart, pick-vs-win scatter |
| `/heroes`   | `pages/Heroes.jsx`    | Sortable table of every hero's latest stats |
| `/balance`  | `pages/Balance.jsx`   | Verdict cards with rationale + recommendation |
| `/predict`  | `pages/Predict.jsx`   | Pick teams, get explainable win probability |
