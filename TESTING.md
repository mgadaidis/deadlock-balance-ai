# Testing Checklist

## Testing Purpose

This document describes the testing performed for the Deadlock Balance AI project.

Testing was based on the project proposal goals and success criteria:

* collect and structure Deadlock data
* calculate useful hero and item metrics
* detect overpowered and underpowered heroes/items
* use machine learning for balance detection
* display results in a structured React frontend
* validate full backend-to-frontend integration

The final system was tested as a local full-stack prototype using:

* FastAPI backend
* SQLite database
* public Deadlock API data
* scikit-learn machine learning model
* React frontend
* Axios API integration
* Recharts visualizations

---

## 1. Backend Startup Testing

### Goal

Confirm that the backend starts correctly and exposes the required API endpoints.

### Test Steps

1. Open terminal in the backend folder.
2. Activate the virtual environment.
3. Start the backend server.

Command used:

```powershell
cd backend
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate
uvicorn app.main:app --reload
```

### Checklist

* [ ] Backend starts without crashing
* [ ] Backend runs at `http://127.0.0.1:8000`
* [ ] Swagger UI opens at `http://127.0.0.1:8000/docs`
* [ ] `/health` endpoint works
* [ ] `/data-status` endpoint works
* [ ] `/diagnose` endpoint works

### Result

Status: Passed

---

## 2. Frontend Startup Testing

### Goal

Confirm that the React frontend starts and connects to the backend.

### Test Steps

1. Open a second terminal.
2. Go to the frontend folder.
3. Start the Vite development server.

Command used:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

### Checklist

* [ ] Frontend starts without crashing
* [ ] App opens at `http://localhost:5173/`
* [ ] Main navigation appears
* [ ] Page styling loads correctly
* [ ] Frontend can call backend through the Vite proxy

### Result

Status: Passed

---

## 3. Data Refresh Testing

### Goal

Confirm that the data pipeline collects public data, processes it, stores it, and makes it available to the frontend.

### Test Steps

1. Open the app.
2. Go to the Overview page.
3. Click **Refresh Data**.
4. Wait until the Dispatch/result box appears.
5. Check inserted counts and warnings.

### Checklist

* [ ] Refresh Data button starts the backend refresh process
* [ ] Hero data is fetched
* [ ] Hero statistics are fetched
* [ ] Item statistics are fetched
* [ ] Data is cleaned and normalized
* [ ] Data is stored in SQLite
* [ ] Balance flags are generated
* [ ] ML model becomes available after refresh
* [ ] Overview page updates after refresh

### Result

Status:  Passed

---

## 4. Database Status Testing

### Goal

Confirm that refreshed data exists in the local database.

### Endpoint Tested

```txt
http://127.0.0.1:8000/data-status
```

### Checklist

* [ ] `heroes` count is greater than 0
* [ ] `hero_stats` count is greater than 0
* [ ] `balance_flags` count is greater than 0
* [ ] `items` count is greater than 0
* [ ] Latest snapshot timestamp appears

### Screenshot Evidence

```txt
docs/screenshots/data-status.png
```

### Result

Status: Passed

---

## 5. Public API Diagnose Testing

### Goal

Confirm whether external Deadlock API data is reachable.

### Endpoint Tested

```txt
http://127.0.0.1:8000/diagnose
```

### Checklist

* [ ] Diagnose endpoint opens
* [ ] Hero API check returns a response
* [ ] Hero stats API check returns a response
* [ ] Item API check returns a response
* [ ] Errors/warnings are visible if external API data is unavailable

### Result

Status:  Passed

---

## 6. Overview Page Testing

### Goal

Confirm that the dashboard displays the main balance statistics and visualizations.

### Page Tested

```txt
Overview
```

### Checklist

* [ ] Overview page loads
* [ ] Refresh Data button is visible
* [ ] Overpowered hero count appears
* [ ] Underpowered hero count appears
* [ ] Balanced hero count appears
* [ ] Win-rate roster chart appears
* [ ] Net-worth spikes chart appears
* [ ] Item tier list appears
* [ ] Meta Shift/current snapshot section appears
* [ ] Footer/source links appear

### Screenshot Evidence

```txt
docs/screenshots/overview.png
```

### Result

Status: Passed

---

## 7. Simulator Page Testing

### Goal

Confirm that the simulator can predict draft outcomes using heroes, optional items, item compatibility, and ML baseline.

### Page Tested

```txt
Simulator
```

### Test Steps

1. Open Simulator.
2. Select heroes for the user team.
3. Select enemy heroes.
4. Optionally select items for heroes.
5. Run the simulation.

### Checklist

* [ ] Simulator page loads
* [ ] User team heroes can be selected
* [ ] Enemy heroes can be selected
* [ ] Item configuration can be opened
* [ ] Items can be selected
* [ ] Full 12-item builds are not required
* [ ] Impossible upgrade combinations are blocked
* [ ] Simulation returns win probability
* [ ] Simulation returns build compatibility
* [ ] Early-game phase explanation appears
* [ ] Mid-game phase explanation appears
* [ ] Late-game phase explanation appears
* [ ] Model note appears

### Screenshot Evidence

```txt
docs/screenshots/simulator.png
```

### Result

Status: Passed

---

## 8. Hero Recommendation Page Testing

### Goal

Confirm that hero balance recommendations use statistics and ML evidence.

### Page Tested

```txt
Hero Recommendation
```

### Checklist

* [ ] Hero Recommendation page loads
* [ ] ML Balance Model section appears
* [ ] Overpowered section appears if available
* [ ] Underpowered section appears if available
* [ ] Balanced section appears
* [ ] Hero recommendation cards appear
* [ ] Evidence text appears
* [ ] ML baseline appears
* [ ] ML gap appears
* [ ] ML balance class appears
* [ ] ML confidence appears
* [ ] Mechanical reasoning appears
* [ ] Macro impact appears
* [ ] Final recommendation appears

### Screenshot Evidence

```txt
docs/screenshots/hero-recommendation.png
```

### Result

Status: Passed

---

## 9. Item Recommendation Page Testing

### Goal

Confirm that item recommendations use win rate, usage rate, confidence, tier, and item category.

### Page Tested

```txt
Item Recommendation
```

### Checklist

* [ ] Item Recommendation page loads
* [ ] Weapon items section appears
* [ ] Spirit items section appears
* [ ] Vitality items section appears
* [ ] Other/unknown item category is not displayed
* [ ] Item rows can be expanded
* [ ] Item win rate appears
* [ ] Usage rate appears
* [ ] Match count appears
* [ ] Confidence appears
* [ ] Item tier appears
* [ ] Evidence appears
* [ ] Simulator impact appears
* [ ] Recommendation appears

### Specific Logic Checked

* [ ] High win rate with low usage is treated as niche
* [ ] High win rate with high usage is treated as stronger balance evidence
* [ ] Low win rate with high usage can be treated as popular but weak
* [ ] Item recommendations are not based on win rate alone

### Screenshot Evidence

```txt
docs/screenshots/item-recommendation.png
```

### Result

Status: Passed

---

## 10. Machine Learning Model Testing

### Goal

Confirm that the app contains a real ML model and that ML results are displayed in the app.

### Endpoint Tested

```txt
http://127.0.0.1:8000/predict/model-status
```

### Checklist

* [ ] `/predict/model-status` endpoint works
* [ ] RandomForestRegressor is shown
* [ ] RandomForestClassifier is shown
* [ ] Training rows are shown
* [ ] Feature list is shown
* [ ] Regression target is shown
* [ ] Classification target is shown
* [ ] ML output appears in Hero Recommendation page
* [ ] ML baseline is visible in recommendation cards
* [ ] ML class/confidence is visible in recommendation cards

### Screenshot Evidence

```txt
docs/screenshots/model-status.png
```

### Result

Status: Passed

---

## 11. API Integration Testing

### Goal

Confirm that frontend pages correctly receive data from backend endpoints.

### Checklist

* [ ] Overview receives data from `/balance/summary`
* [ ] Overview receives hero stats from `/heroes/stats`
* [ ] Overview receives item tiers from `/items/tier-list`
* [ ] Hero Recommendation receives data from `/balance/flags`
* [ ] Item Recommendation receives data from `/items/recommendations`
* [ ] Simulator receives results from `/predict`
* [ ] Model status data loads from `/predict/model-status`
* [ ] Frontend handles loading states without crashing

### Result

Status: Passed

---

## 12. Item Upgrade Restriction Testing

### Goal

Confirm that item upgrade restrictions work correctly in the simulator.

### Test Example

Rapid Rounds can upgrade into Swift Striker or Burst Fire.

Expected logic:

* Rapid Rounds blocks Swift Striker
* Rapid Rounds blocks Burst Fire
* Swift Striker blocks Rapid Rounds
* Burst Fire blocks Rapid Rounds
* Swift Striker does not incorrectly block Burst Fire
* Burst Fire does not incorrectly block Swift Striker

### Checklist

* [ ] Base item blocks direct upgrades
* [ ] Upgraded item blocks base item
* [ ] Sibling upgrades do not incorrectly block each other
* [ ] Simulator disables invalid item combinations
* [ ] Valid sibling upgrades remain selectable

### Result

Status:  Passed

---

## 13. Automated Smoke Testing

### Goal

Confirm that the main app pages and backend status endpoints can be opened automatically.

### Tool

```txt
Playwright
```

### Test File

```txt
frontend/tests/smoke.spec.cjs
```

### Automated Test Checks

* [ ] Opens Overview page
* [ ] Opens Simulator page
* [ ] Opens Hero Recommendation page
* [ ] Opens Item Recommendation page
* [ ] Opens `/predict/model-status`
* [ ] Opens `/data-status`
* [ ] Captures screenshots into `docs/screenshots/`

### Command Used

```powershell
cd frontend
npx playwright test tests/smoke.spec.cjs
```

### Result

Status: Passed

---

## 14. Screenshot Evidence

The following screenshots should be included:

```txt
docs/screenshots/overview.png
docs/screenshots/simulator.png
docs/screenshots/hero-recommendation.png
docs/screenshots/item-recommendation.png
docs/screenshots/model-status.png
docs/screenshots/data-status.png
```


---

## 15. Final End-to-End User Flow

### Goal

Confirm that the full project works as a complete system.

### Full Flow

1. Start backend.
2. Start frontend.
3. Open frontend in browser.
4. Click Refresh Data.
5. Confirm Overview data appears.
6. Open Simulator.
7. Select heroes and optional items.
8. Run simulation.
9. Confirm prediction result appears.
10. Open Hero Recommendation.
11. Confirm ML evidence appears.
12. Open Item Recommendation.
13. Confirm item recommendation details appear.
14. Open `/predict/model-status`.
15. Open `/data-status`.

### Checklist

* [ ] Full flow completed successfully
* [ ] No critical frontend errors appeared
* [ ] No backend crash occurred
* [ ] Main project features worked as expected

### Result

Status: Passed

---

## Final Testing Summary

The final project was tested as a local full-stack prototype.

The testing confirmed that:

* the backend starts correctly
* the frontend starts correctly
* data refresh works
* hero and item statistics are loaded
* balance recommendations appear
* ML model status is available
* simulator predictions work
* item recommendation logic works
* frontend pages display backend results
* screenshot evidence is available

Overall status: Passed
