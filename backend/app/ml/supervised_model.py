"""
Supervised ML layer for Deadlock Balance AI.

This module contains the project's explicit machine-learning implementation.
It trains two Random Forest models from the latest refreshed public aggregate
hero data:

1) RandomForestRegressor
   Target: numeric hero win-rate baseline.
   Use: simulator and recommendation cross-checks.

2) RandomForestClassifier
   Target: balance class (overpowered / balanced / underpowered), derived from
   configured win-rate thresholds.
   Use: visible balance-detection classification inside recommendation cards.

The public API provides aggregate hero rows rather than full match/replay rows,
so the model is intentionally framed as a supervised balance-detection baseline,
not a professional matchmaker. The rule-based explanation layer remains present
so results are interpretable.
"""
from __future__ import annotations

from collections import Counter
from threading import RLock
from dataclasses import dataclass
from math import log1p
from statistics import mean

import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings

ROLE_KEYS = ("marksman", "mystic", "brawler", "support", "unknown")
CLASS_LABELS = ("underpowered", "balanced", "overpowered")

# Training Random Forests repeatedly on every page request made data feel slow
# because Recommendations and model-status can be called at the same time.
# Cache the trained models per latest DB snapshot; a new Refresh uses a new
# fetched_at timestamp, so the cache naturally retrains only when data changes.
_MODEL_CACHE: dict[str, object] = {"snapshot": None, "bundle": None}
_MODEL_LOCK = RLock()


def clear_model_cache() -> None:
    with _MODEL_LOCK:
        _MODEL_CACHE["snapshot"] = None
        _MODEL_CACHE["bundle"] = None



@dataclass
class ModelBundle:
    model: Pipeline                    # Regression model kept as .model for compatibility.
    rows: int
    mae: float | None
    feature_names: list[str]
    snapshot: object
    classifier: Pipeline | None = None
    classifier_accuracy: float | None = None
    classifier_classes: list[str] | None = None


def _latest_snapshot(db: Session):
    return db.execute(
        select(models.HeroStat.fetched_at)
        .order_by(desc(models.HeroStat.fetched_at))
        .limit(1)
    ).scalar()


def _latest_rows(db: Session) -> list[models.HeroStat]:
    ts = _latest_snapshot(db)
    if ts is None:
        return []
    return db.execute(
        select(models.HeroStat)
        .where(models.HeroStat.fetched_at == ts)
    ).scalars().all()


def _role(hero: models.Hero | None) -> str:
    if not hero or not hero.role:
        raw = ""
    else:
        raw = hero.role.lower().strip()
    for key in ROLE_KEYS[:-1]:
        if key in raw:
            return key
    text = f"{hero.role_text or ''} {hero.playstyle or ''}".lower() if hero else ""
    if any(w in text for w in ("bullet", "gun", "snipe", "shoot", "marksman")):
        return "marksman"
    if any(w in text for w in ("spirit", "mystic", "curse", "ability", "turret", "zone")):
        return "mystic"
    if any(w in text for w in ("front", "close combat", "sustain", "charge", "bulk")):
        return "brawler"
    if any(w in text for w in ("heal", "rescue", "support", "shield")):
        return "support"
    return "unknown"


def feature_vector(stat: models.HeroStat, hero: models.Hero | None) -> list[float]:
    role = _role(hero)
    matches = max(int(stat.matches or 0), 0)
    deaths = float(stat.avg_deaths or 0.0)
    kda = float(stat.kda or 0.0)
    damage = float(stat.avg_damage or 0.0)
    net = float(stat.avg_net_worth or 0.0)
    kills = float(stat.avg_kills or 0.0)
    assists = float(stat.avg_assists or 0.0)
    pick_rate = float(stat.pick_rate or 0.0)

    # Format raw API rows into numeric ML features. Large values are scaled, and
    # win_rate is excluded because it is the regression target and is used to
    # derive the classification label.
    vec = [
        log1p(matches),
        pick_rate,
        kills,
        deaths,
        assists,
        kda,
        damage / 10000.0,
        net / 10000.0,
        kills / max(deaths, 0.35),
        assists / max(deaths, 0.35),
    ]
    vec.extend(1.0 if role == r else 0.0 for r in ROLE_KEYS)
    return vec


FEATURE_NAMES = [
    "log_matches", "pick_rate", "avg_kills", "avg_deaths", "avg_assists", "kda",
    "avg_damage_10k", "avg_net_worth_10k", "kills_per_death", "assists_per_death",
    *[f"role_{r}" for r in ROLE_KEYS],
]


def balance_label(win_rate: float) -> str:
    if win_rate > settings.winrate_high:
        return "overpowered"
    if win_rate < settings.winrate_low:
        return "underpowered"
    return "balanced"


def _regressor() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("rf_regressor", RandomForestRegressor(
            n_estimators=260,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=None,
        )),
    ])


def _classifier() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("rf_classifier", RandomForestClassifier(
            n_estimators=320,
            min_samples_leaf=1,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=None,
        )),
    ])


def train_hero_winrate_model(db: Session) -> ModelBundle | None:
    snapshot = _latest_snapshot(db)
    with _MODEL_LOCK:
        if _MODEL_CACHE.get("snapshot") == snapshot:
            return _MODEL_CACHE.get("bundle")  # type: ignore[return-value]

        rows = [r for r in _latest_rows(db) if (r.matches or 0) >= 50]
        if len(rows) < 12:
            _MODEL_CACHE["snapshot"] = snapshot
            _MODEL_CACHE["bundle"] = None
            return None

        X, y_reg, y_cls = [], [], []
        for stat in rows:
            hero = db.get(models.Hero, stat.hero_id)
            X.append(feature_vector(stat, hero))
            wr = float(stat.win_rate or 0.5)
            y_reg.append(wr)
            y_cls.append(balance_label(wr))

        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y_reg, dtype=float)

        reg = _regressor()
        mae = None
        if len(rows) >= 16 and len(set(round(v, 4) for v in y_reg)) > 3:
            folds = min(5, len(rows))
            try:
                preds = cross_val_predict(reg, X_arr, y_arr, cv=KFold(n_splits=folds, shuffle=True, random_state=42))
                mae = float(mean_absolute_error(y_arr, preds))
            except Exception:
                mae = None
        reg.fit(X_arr, y_arr)

        clf = None
        clf_acc = None
        clf_classes = sorted(set(y_cls), key=lambda c: CLASS_LABELS.index(c) if c in CLASS_LABELS else 99)
        counts = Counter(y_cls)
        if len(clf_classes) >= 2:
            clf = _classifier()
            min_class = min(counts.values())
            if len(rows) >= 16 and min_class >= 2:
                folds = min(5, min_class)
                try:
                    preds = cross_val_predict(clf, X_arr, np.asarray(y_cls), cv=StratifiedKFold(n_splits=folds, shuffle=True, random_state=42))
                    clf_acc = float(accuracy_score(y_cls, preds))
                except Exception:
                    clf_acc = None
            clf.fit(X_arr, np.asarray(y_cls))

        bundle = ModelBundle(
            model=reg,
            rows=len(rows),
            mae=mae,
            feature_names=list(FEATURE_NAMES),
            snapshot=snapshot,
            classifier=clf,
            classifier_accuracy=clf_acc,
            classifier_classes=clf_classes,
        )
        _MODEL_CACHE["snapshot"] = snapshot
        _MODEL_CACHE["bundle"] = bundle
        return bundle


def predict_hero_baseline(bundle: ModelBundle | None, db: Session, stat: models.HeroStat) -> float | None:
    if bundle is None:
        return None
    hero = db.get(models.Hero, stat.hero_id)
    x = np.asarray([feature_vector(stat, hero)], dtype=float)
    pred = float(bundle.model.predict(x)[0])
    return max(0.35, min(0.65, pred))


def predict_balance_class(bundle: ModelBundle | None, db: Session, stat: models.HeroStat) -> dict | None:
    if bundle is None or bundle.classifier is None:
        return None
    hero = db.get(models.Hero, stat.hero_id)
    x = np.asarray([feature_vector(stat, hero)], dtype=float)
    label = str(bundle.classifier.predict(x)[0])
    confidence = None
    probabilities: dict[str, float] = {}
    if hasattr(bundle.classifier, "predict_proba"):
        try:
            proba = bundle.classifier.predict_proba(x)[0]
            classes = list(bundle.classifier.named_steps["rf_classifier"].classes_)
            probabilities = {str(c): float(p) for c, p in zip(classes, proba)}
            confidence = float(max(proba))
        except Exception:
            confidence = None
    return {"label": label, "confidence": confidence, "probabilities": probabilities}


def predict_team_baseline(bundle: ModelBundle | None, db: Session, team: list[models.HeroStat]) -> tuple[float | None, list[str]]:
    if bundle is None or not team:
        return None, []
    preds: list[float] = []
    notes: list[str] = []
    for stat in team:
        pred = predict_hero_baseline(bundle, db, stat)
        if pred is None:
            continue
        preds.append(pred)
        hero = db.get(models.Hero, stat.hero_id)
        name = hero.name if hero else f"Hero #{stat.hero_id}"
        delta = pred - float(stat.win_rate or 0.5)
        direction = "above" if delta >= 0 else "below"
        cls = predict_balance_class(bundle, db, stat)
        cls_text = f" ML classifier reads {cls['label']}" + (f" at {cls['confidence']:.0%} confidence" if cls and cls.get('confidence') is not None else "") + "." if cls else ""
        notes.append(
            f"ML regression baseline for {name}: {pred:.1%}, {abs(delta):.1%} {direction} the raw aggregate win rate after considering KDA, damage, economy, pick rate, sample size, and role." + cls_text
        )
    return (float(mean(preds)) if preds else None), notes[:6]


def model_status(db: Session) -> dict:
    bundle = train_hero_winrate_model(db)
    if bundle is None:
        return {
            "available": False,
            "model_family": "Supervised Random Forest",
            "training_rows": 0,
            "features": FEATURE_NAMES,
            "regression": {"model_type": "RandomForestRegressor", "target": "hero win_rate", "cross_validated_mae": None},
            "classification": {"model_type": "RandomForestClassifier", "target": "balance class", "classes": [], "cross_validated_accuracy": None},
            "message": "Not enough refreshed hero rows are available to train the supervised ML models. Run Refresh Data first.",
        }
    return {
        "available": True,
        "model_family": "Supervised Random Forest",
        "training_rows": bundle.rows,
        "features": bundle.feature_names,
        "snapshot": str(bundle.snapshot),
        "regression": {
            "model_type": "RandomForestRegressor",
            "target": "numeric hero win-rate baseline",
            "cross_validated_mae": bundle.mae,
        },
        "classification": {
            "model_type": "RandomForestClassifier",
            "target": "balance class: overpowered / balanced / underpowered",
            "classes": bundle.classifier_classes or [],
            "cross_validated_accuracy": bundle.classifier_accuracy,
        },
        "message": "Supervised ML trained on the latest public hero-stat snapshot. The regressor predicts expected win-rate baseline, while the classifier predicts the balance category. Recommendations compare observed performance against these ML outputs before presenting a final decision.",
    }
