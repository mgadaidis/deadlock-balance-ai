# Data Pipeline

## Overview

The data pipeline is responsible for converting public Deadlock data into useful balance information for the app.

The pipeline starts when the user clicks **Refresh Data** on the Overview page.

The backend then collects data, cleans it, calculates important statistics, stores the results in SQLite, generates recommendations, and prepares data for the frontend.

Main file:

```txt
backend/app/data_pipeline.py
```

---

## Pipeline Goal

The main goal of the pipeline is to support data-driven game balance analysis.

It helps the system answer questions such as:

* Which heroes are overperforming?
* Which heroes are underperforming?
* Which heroes are close to balanced?
* Which items are strong, weak, or niche?
* Does the ML model agree with the observed statistics?
* Can the simulator use hero and item data for predictions?

---

## Data Sources

The project uses public Deadlock data.

The main public data source is:

```txt
deadlock-api.com
```

The app also references public sources in the footer for transparency, such as Statlocker and Liquipedia.

The project does not use private developer data, individual player tracking, or live match replay data.

---

## Refresh Flow

When Refresh Data is clicked, the pipeline follows this process:

1. Fetch hero metadata
2. Fetch hero statistics
3. Fetch item statistics
4. Filter invalid or unreleased heroes
5. Clean and normalize values
6. Calculate hero metrics
7. Calculate item metrics
8. Store data in SQLite
9. Generate hero balance flags
10. Generate item tiers and item recommendations
11. Prepare simulator data
12. Train or warm the machine learning model
13. Return refresh results to the frontend

---

## Data Cleaning

Public API data can contain missing values, renamed fields, or unavailable endpoints.

The backend handles this by:

* safely converting values into numbers
* avoiding division by zero
* ignoring invalid rows
* filtering unreleased/test heroes
* using fallback behavior when optional data is missing
* storing usable data locally

This helps prevent the app from crashing when the public API changes or returns incomplete data.

---

## Hero Metrics

The pipeline calculates important hero statistics, including:

* matches
* wins
* losses
* win rate
* pick rate
* average kills
* average deaths
* average assists
* KDA
* average damage
* average net worth

### Win Rate

```txt
wins / matches
```

### Pick Rate

```txt
hero matches / total hero matches
```

### KDA

```txt
(kills + assists) / deaths
```

If deaths are zero, the backend avoids division by zero.

---

## Item Metrics

The pipeline also processes item data.

For items, the app stores and calculates:

* item name
* category
* matches
* wins
* win rate
* usage rate
* confidence
* tier
* icon
* upgrade restrictions

Item categories include:

* weapon
* spirit
* vitality

---

## Item Usage Rate

Usage rate is important because win rate alone can be misleading.

For example:

* high win rate + high usage = stronger balance signal
* high win rate + low usage = niche item, not automatically overpowered
* low win rate + high usage = popular but possibly inefficient item
* low win rate + low usage = low-priority or niche weak item

This makes item recommendations more realistic.

---

## Item Confidence

Confidence shows how reliable an item result is.

The system gives more trust to items with a larger sample size.

Example:

```txt
High matches = higher confidence
Low matches = lower confidence
```

This prevents the app from overreacting to small-sample win rates.

---

## Item Upgrade Logic

Item upgrade paths are stored in a separate data file:

```txt
backend/app/data/item_upgrade_paths.json
```

This keeps item logic separate from hardcoded application code.

Example:

```txt
Rapid Rounds -> Swift Striker
Rapid Rounds -> Burst Fire
```

The simulator uses direct parent-upgrade logic:

* Rapid Rounds blocks Swift Striker
* Rapid Rounds blocks Burst Fire
* Swift Striker blocks Rapid Rounds
* Burst Fire blocks Rapid Rounds
* Swift Striker does not incorrectly block Burst Fire
* Burst Fire does not incorrectly block Swift Striker

This prevents impossible item combinations while avoiding incorrect sibling restrictions.

---

## Database Storage

The project uses SQLite as a local database/cache.

The database stores:

* heroes
* hero statistics
* balance flags
* item statistics
* ability path data if available

The local database makes the app faster because it does not need to call the public API every time the user changes pages.

Database files are ignored by Git and are not committed.

---

## Snapshot System

Each refresh creates a new data snapshot.

This allows the app to compare the latest data with previous data.

The Meta Shift section uses snapshots to show:

* hero win rate movement
* hero pick rate movement
* rising heroes
* falling heroes

If only one snapshot exists, the app displays the current baseline instead of movement.

---

## Balance Flag Generation

After hero metrics are calculated, the backend generates balance flags.

Heroes can be classified as:

* overpowered
* underpowered
* balanced

The system considers:

* win rate
* pick rate
* KDA
* damage
* net worth
* deaths
* anomaly signals
* ML model comparison

This is better than using win rate alone.

---

## Machine Learning Preparation

After cleaned hero data is stored, it is formatted for machine learning.

The model receives numerical features such as:

* matches
* pick rate
* kills
* deaths
* assists
* KDA
* damage
* net worth
* role information

The ML model predicts expected win rate and balance class.

The result is shown on the Hero Recommendation page as a model cross-check.

---

## Frontend Output

After the pipeline finishes, the frontend can display:

* hero summary counts
* win-rate chart
* net-worth chart
* item tier list
* meta shift table
* simulator results
* hero recommendations
* item recommendations
* ML model status

---

## Pipeline Limitations

The project depends on public aggregate data.

Because of this, the system does not include:

* private developer APIs
* full replay logs
* individual player tracking
* exact ability-level damage data
* perfect item-build win rate for every hero

The system is still useful as an academic prototype because it demonstrates a full data pipeline, statistical analysis, ML-based balance detection, and a working dashboard.

---

## Summary

The data pipeline connects the full system together.

It transforms public game data into structured information that can be used by the backend, ML model, simulator, and frontend dashboard.

The pipeline supports the main goal of the project: making game balance analysis more data-driven, explainable, and easier to review.