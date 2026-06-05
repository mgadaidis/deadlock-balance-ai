# API Endpoints
## Overview

The backend of Deadlock Balance AI is built with FastAPI. It provides REST API endpoints that allow the frontend to request hero statistics, item statistics, balance recommendations, simulator predictions, and machine learning model information.

Backend development URL:

```txt
http://127.0.0.1:8000
```

Swagger UI:

```txt
http://127.0.0.1:8000/docs
```

The frontend communicates with these endpoints using Axios.

---

## System Endpoints

### GET `/health`

Checks if the backend is running.

**Purpose:**

Used for a quick backend status check.

**Expected result:**

Returns a simple response showing that the backend is active.

---

### GET `/data-status`

Shows the current local database status.

**Purpose:**

Used to confirm whether data exists in the local SQLite database.

**Returns information such as:**

* hero count
* hero statistics count
* balance flag count
* item count
* ability path count
* latest snapshot timestamp

**Used for:**

* checking whether Refresh Data worked
* testing database status
* screenshot evidence

---

### GET `/diagnose`

Checks whether external/public Deadlock API data is reachable.

**Purpose:**

Used for debugging public API problems.

**Useful when:**

* Refresh Data is slow
* some data does not load
* the public API returns empty results
* the frontend shows missing data

---

### POST `/refresh`

Runs the full data refresh pipeline.

**Purpose:**

This is one of the most important endpoints in the project.

It:

1. fetches hero metadata
2. fetches hero statistics
3. fetches item statistics
4. cleans and normalizes data
5. stores data in SQLite
6. generates balance flags
7. updates item tiers and item recommendations
8. prepares or updates the ML model

**Used by:**

The **Refresh Data** button on the Overview page.

---

## Hero Endpoints

### GET `/heroes`

Returns available heroes.

**Purpose:**

Used to provide hero information to the frontend and simulator.

---

### GET `/heroes/stats`

Returns the latest hero statistics snapshot.

**Includes data such as:**

* hero name
* matches
* wins
* losses
* win rate
* pick rate
* KDA
* damage
* net worth

**Used by:**

* Overview charts
* Simulator
* Hero Recommendation page

---

### GET `/heroes/{id}/stats`

Returns historical statistics for one hero.

**Purpose:**

Used for checking how one hero changes over time.

---

### GET `/heroes/{id}/abilities`

Returns ability path information for a hero if available from the public API.

**Note:**

The project does not invent ability data. If ability data is unavailable, this endpoint may return an empty result.

---

## Balance Endpoints

### GET `/balance/summary`

Returns a summary of hero balance categories.

**Returns counts for:**

* overpowered heroes
* underpowered heroes
* balanced heroes

**Used by:**

Overview page summary cards.

---

### GET `/balance/flags`

Returns hero balance recommendations.

**Each result can include:**

* hero name
* verdict
* score
* evidence
* mechanical reasoning
* macro impact
* recommendation
* ML baseline
* ML gap
* ML class
* ML confidence

**Used by:**

Hero Recommendation page.

---

### GET `/balance/meta-shift`

Returns hero performance movement between snapshots.

**Purpose:**

Used to compare the latest data snapshot with the previous snapshot.

**Can show:**

* rising heroes
* falling heroes
* win rate change
* pick rate change

If only one snapshot exists, the frontend displays the current baseline instead.

---

## Item Endpoints

### GET `/items`

Returns latest item statistics.

**Can include:**

* item name
* item category
* matches
* win rate
* confidence
* tier
* icon
* upgrade restrictions

---

### GET `/items/tier-list`

Returns items grouped into tiers.

**Tiers:**

* S
* A
* B
* C
* D

**Used by:**

Overview page item tier list.

---

### GET `/items/recommendations`

Returns item recommendations grouped by category.

**Categories:**

* weapon
* spirit
* vitality

**Each item recommendation can include:**

* item win rate
* usage rate
* match count
* confidence
* tier
* evidence
* simulator impact
* recommendation
* direct item exclusions

**Important logic:**

Item recommendations are not based only on win rate. Usage rate and confidence are also considered.

For example, an item with high win rate but low usage is treated as niche instead of automatically overpowered.

---

## Prediction and ML Endpoints

### POST `/predict`

Runs the simulator.

**Purpose:**

Predicts a draft result based on selected heroes and optional item builds.

**Input includes:**

* user team heroes
* enemy team heroes
* optional item builds

**Output includes:**

* win probability
* team average win rate
* enemy average win rate
* build compatibility
* item impact
* early-game explanation
* mid-game explanation
* late-game explanation
* final summary
* model note

**Used by:**

Simulator page.

---

### GET `/predict/model-status`

Returns machine learning model status.

**Purpose:**

Used to prove that the project includes a real ML model.

**Can show:**

* model type
* training rows
* feature names
* regression target
* classifier classes
* model performance information

**Used by:**

* Hero Recommendation page
* testing evidence
* final presentation

---

## API Testing

Important endpoints tested during development:

```txt
GET /health
GET /data-status
GET /diagnose
POST /refresh
GET /heroes/stats
GET /balance/summary
GET /balance/flags
GET /items/tier-list
GET /items/recommendations
POST /predict
GET /predict/model-status
```

These endpoints confirm that the backend, database, data refresh pipeline, ML model, and frontend integration work correctly.

