# ML Model

## Overview

Deadlock Balance AI uses supervised machine learning to support hero balance analysis.

The model is not meant to perfectly predict every match. Instead, it provides a data-based second opinion for hero balance recommendations.

The ML model helps answer:

```txt
Is this hero performing normally for their statistics, or are they performing above/below what the model expects?
```

The ML output is mainly shown in the Hero Recommendation page and the `/predict/model-status` endpoint.

---

## Why Machine Learning Is Used

Traditional game balance analysis can be subjective and slow.

Win rate alone is also not enough, because a hero can have a high or low win rate for many reasons, such as:

* low sample size
* low pick rate
* player skill
* unusual builds
* strong economy
* high damage
* high survivability
* role differences

The ML model helps compare a hero’s observed win rate with an expected win rate based on other statistics.

This makes recommendations more data-driven and explainable.

---

## Models Used

The backend uses two Random Forest models from scikit-learn:

* `RandomForestRegressor`
* `RandomForestClassifier`

Main file:

```txt
backend/app/ml/supervised_model.py
```

---

## RandomForestRegressor

The `RandomForestRegressor` predicts a hero’s expected win rate.

It answers:

```txt
Based on this hero's statistics, what win rate should the hero approximately have?
```

The app then compares:

```txt
observed win rate vs ML expected win rate
```

Example:

```txt
Observed win rate: 56.1%
ML expected win rate: 54.9%
Gap: +1.2 percentage points
```

This means the hero is performing slightly above what the model expected.

---

## RandomForestClassifier

The `RandomForestClassifier` predicts the hero’s balance class.

Possible classes:

* overpowered
* balanced
* underpowered

This classification is used as an additional balance signal in the Hero Recommendation page.

---

## Input Features

The model uses hero performance features such as:

* match count
* pick rate
* average kills
* average deaths
* average assists
* KDA
* average damage
* average net worth
* kills per death
* assists per death
* hero role

Hero role is converted into numerical features so that the model can process it.

---

## Target Values

### Regression Target

The regression target is:

```txt
hero win rate
```

The regressor learns how hero statistics relate to expected win rate.

### Classification Target

The classification target is the balance class:

```txt
overpowered
balanced
underpowered
```

The class is based on the project’s balance thresholds.

---

## Data Formatting

Before training, the backend converts raw hero rows into a numerical feature vector.

Example feature format:

```txt
[
  log_matches,
  pick_rate,
  avg_kills,
  avg_deaths,
  avg_assists,
  kda,
  avg_damage_scaled,
  avg_net_worth_scaled,
  kills_per_death,
  assists_per_death,
  role_features
]
```

Large values such as damage and net worth are scaled down so that the model can process them more effectively.

Missing or unsafe values are handled before training.

---

## Training Process

The model trains on the latest refreshed hero statistics snapshot.

Training flow:

1. Refresh Data runs.
2. Hero statistics are stored in SQLite.
3. The backend loads the latest hero stats.
4. Rows with enough match data are selected.
5. Features are generated.
6. RandomForestRegressor is trained.
7. RandomForestClassifier is trained if enough class data exists.
8. The model is cached for faster app loading.

The model does not retrain every time the user changes pages. It is cached after training and updated again after a new refresh.

---

## Model Output in the App

The Hero Recommendation page can show:

* ML expected win rate
* observed win rate
* ML gap
* ML balance class
* ML confidence
* explanation of whether the ML model supports the recommendation

This makes the recommendation more understandable.

---

## Model Status Endpoint

The ML model can be checked at:

```txt
http://127.0.0.1:8000/predict/model-status
```

This endpoint can show:

* whether the model is available
* model type
* training row count
* feature names
* regression target
* classifier classes
* model performance information when available

This endpoint is useful for testing and presentation because it proves that the backend has an ML component.

---

## How ML Supports Recommendations

The app does not blindly trust the ML model.

Instead, ML is used as a cross-check.

Example:

```txt
Observed win rate: 56.1%
ML baseline: 54.9%
Hero is +1.2 percentage points above expected performance.
```

This strengthens an overperformance signal.

If the observed win rate is close to the ML baseline, the app treats the result as less extreme.

---

## ML and Simulator

The simulator can use ML baseline information as part of its prediction logic.

The simulator also considers:

* selected heroes
* enemy heroes
* item builds
* item compatibility
* build quality
* early/mid/late phase signals

The ML model is one signal inside the larger simulator logic.

---

## Item Recommendations and ML

Hero balance recommendations use ML.

Item recommendations are mostly statistical and rule-based.

Item recommendations consider:

* item win rate
* usage rate
* match count
* confidence
* tier
* category
* upgrade restrictions

This is because full hero-item build datasets are limited or unavailable from public sources.

A future version could train a separate item compatibility model if detailed hero-item build data becomes available.

---

## Limitations

The model uses public aggregate data, not full replay data.

Because of this, it cannot perfectly understand:

* exact ability damage
* exact player skill
* complete item build timing
* full match context
* team coordination
* replay-level combat events

The model is still useful because it provides an explainable prototype for data-driven game balance analysis.

---

## Summary

The machine learning component improves the project by giving a model-based comparison for hero balance.

It helps make the system more objective than simple win-rate analysis and supports the project goal of AI-assisted game balance recommendations.
message.txt
7 KB