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

When **Refresh Data** is clicked, the pipeline follows this process:

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
win rate = wins / matches
```

Win rate shows how often a hero wins compared to how many matches they appeared in.

A high win rate can suggest overperformance, while a low win rate can suggest underperformance. However, win rate is not used alone because it can be misleading without context.

### Pick Rate

```txt
pick rate = hero matches / total hero matches
```

Pick rate shows how often a hero appears compared to all hero appearances.

Pick rate helps show whether a hero is commonly used or only played in niche situations.

For example:

* high win rate + high pick rate = stronger overperformance signal
* high win rate + low pick rate = possible niche/specialist hero
* low win rate + high pick rate = popular but possibly weak hero

### KDA

```txt
KDA = (kills + assists) / deaths
```

KDA is used to measure combat performance.

If deaths are zero, the backend avoids division by zero by using a safe fallback value.

KDA is useful because two heroes may have similar win rates but very different combat impact.

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

Item usage rate shows how common an item is compared to all item-stat matches.

```txt
item usage rate = item matches / total item matches
```

Usage rate is important because win rate alone can be misleading.

For example:

* high win rate + high usage = stronger balance signal
* high win rate + low usage = niche item, not automatically overpowered
* low win rate + high usage = popular but possibly inefficient item
* low win rate + low usage = low-priority or niche weak item

This makes item recommendations more realistic.

---

## Item Confidence

Confidence shows how reliable an item result is based on sample size.

The system gives more trust to items with a larger sample size.

```txt
higher match count = higher confidence
lower match count = lower confidence
```

This prevents the app from overreacting to small-sample win rates.

For example, an item with 58% win rate over a small number of matches may be less reliable than an item with 52% win rate over thousands of matches.

---

## Mathematical and Statistical Logic

The project uses several basic statistical formulas to convert raw match data into useful balance indicators.

### Win Rate

```txt
win rate = wins / matches
```

Win rate is used for both heroes and items.

It is one of the main indicators of performance, but it is not treated as the only proof of imbalance.

### Pick Rate

```txt
pick rate = hero matches / total hero matches
```

Pick rate helps explain how popular or common a hero is.

A hero with high win rate and high pick rate is usually a stronger balance concern than a hero with high win rate and very low pick rate.

### KDA

```txt
KDA = (kills + assists) / deaths
```

KDA helps measure combat contribution.

The backend handles zero deaths safely to avoid division errors.

### Item Usage Rate

```txt
item usage rate = item matches / total item matches
```

Usage rate is used to understand whether an item is widely used or niche.

This helps prevent bad conclusions such as calling a rarely used item overpowered only because it has a high win rate.

### Confidence

Confidence represents how reliable the result is.

The app treats larger sample sizes as more reliable and smaller sample sizes as less reliable.

This is important because small samples can produce misleading percentages.

### Balance Thresholds

The system uses win-rate thresholds to help classify heroes.

```txt
win rate above healthy range = overpowered signal
win rate inside healthy range = balanced signal
win rate below healthy range = underpowered signal
```

These thresholds are combined with other metrics such as pick rate, KDA, damage, net worth, anomaly signals, and ML baseline comparison.

This makes the system more reliable than using win rate alone.

### ML Gap

The machine learning model predicts an expected win rate for each hero.

The app compares the observed win rate with the ML expected win rate.

```txt
ML gap = observed win rate - ML expected win rate
```

Example:

```txt
Observed win rate: 56.1%
ML expected win rate: 54.9%
ML gap: +1.2 percentage points
```

A positive gap means the hero is performing above the model’s expectation.

A negative gap means the hero is performing below the model’s expectation.

This helps the app decide whether the observed result is unusual compared to the hero’s overall statistical profile.

### Snapshot Difference

Meta Shift compares the latest data snapshot with the previous snapshot.

```txt
win rate change = current win rate - previous win rate
pick rate change = current pick rate - previous pick rate
```

This helps identify heroes that are rising or falling in the current meta.

### Simulator Logic

The simulator combines multiple signals to estimate a win probability.

It considers:

* selected team heroes
* enemy team heroes
* hero win rates
* ML baseline
* item strength
* item compatibility
* build quality
* early/mid/late phase signals

The final output is a probability-style result rather than a guaranteed prediction.

This means the simulator estimates which team has a stronger statistical position, but it does not claim to perfectly predict a real match.

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
