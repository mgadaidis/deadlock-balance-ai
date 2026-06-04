"""Balance recommendations endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .. import ability_service, models, schemas
from ..ml import supervised_model
from ..database import get_db

router = APIRouter(prefix="/balance", tags=["balance"])

def _ml_recommendation_read(predicted: float | None, observed: float, verdict: str) -> tuple[float | None, str | None, str]:
    """Turn the trained model's expected baseline into recommendation evidence.

    The recommendation keeps the existing transparent rule-based verdict, then
    uses ML as a second opinion: does the hero outperform or underperform what
    the model expects from KDA, damage, deaths, economy, pick rate, sample size,
    and role?
    """
    if predicted is None:
        return None, None, (
            "ML evidence: supervised model unavailable because there are not enough refreshed rows to train yet."
        )

    gap = observed - predicted
    gap_pp = gap * 100.0
    base = (
        f"ML evidence: observed win rate {observed:.1%} vs trained model baseline "
        f"{predicted:.1%} ({gap_pp:+.1f} percentage points). "
    )

    if abs(gap) < 0.010:
        interp = (
            base
            + "The model broadly agrees with the raw result, so the case should be treated as normal for this hero's current statistical profile."
        )
    elif gap > 0:
        interp = (
            base
            + "The hero is performing above what the supervised model expects from its KDA, damage, economy, sample size, pick rate and role. "
              "This strengthens an overperformance/watchlist signal and suggests the issue is not just explained by normal role profile."
        )
    else:
        interp = (
            base
            + "The hero is performing below what the supervised model expects from its statistical profile. "
              "This strengthens an underperformance signal, or weakens an overpowered verdict if raw win rate alone looked high."
        )

    return predicted, gap, interp


def _ml_adjusted_recommendation(original: str, verdict: str, gap: float | None) -> str:
    if gap is None:
        return original + " ML cross-check: unavailable until the model has enough refreshed hero rows."
    abs_gap = abs(gap)
    if abs_gap < 0.010:
        return original + " ML cross-check: the trained baseline is close to the observed result, so keep the normal recommendation priority."
    if verdict == "overpowered":
        if gap > 0.015:
            return original + " ML cross-check: prioritize this case because the observed win rate is meaningfully above the model's expected baseline."
        if gap < -0.015:
            return original + " ML cross-check: apply extra caution because the model expected an even stronger baseline; verify with build/ability data before shipping a nerf."
    if verdict == "underpowered":
        if gap < -0.015:
            return original + " ML cross-check: prioritize this case because the observed win rate is meaningfully below the model's expected baseline."
        if gap > 0.015:
            return original + " ML cross-check: lower the urgency because the model sees the hero performing better than the raw verdict implies."
    if verdict == "balanced":
        if gap > 0.020:
            return original + " ML cross-check: keep on watchlist because observed performance is above the model baseline even though the hero remains in the healthy band."
        if gap < -0.020:
            return original + " ML cross-check: keep on watchlist because observed performance is below the model baseline even though the hero remains in the healthy band."
    return original + " ML cross-check: use the model gap as secondary evidence, not as a standalone balance decision."



@router.get("/flags", response_model=list[schemas.BalanceFlagOut])
def latest_flags(verdict: str | None = None, db: Session = Depends(get_db)):
    latest = db.execute(
        select(models.BalanceFlag.created_at).order_by(desc(models.BalanceFlag.created_at)).limit(1)
    ).first()
    if latest is None:
        raise HTTPException(404, "No analysis yet — call POST /refresh first.")
    ts: datetime = latest[0]

    stmt = (
        select(
            models.BalanceFlag, models.Hero.name, models.Hero.image_url,
            models.Hero.role_text, models.Hero.playstyle,
            models.HeroStat.win_rate, models.HeroStat.pick_rate,
            models.HeroStat.kda, models.HeroStat.avg_damage,
        )
        .join(models.Hero, models.Hero.id == models.BalanceFlag.hero_id)
        .join(models.HeroStat,
              (models.HeroStat.hero_id == models.BalanceFlag.hero_id)
              & (models.HeroStat.fetched_at == ts))
        .where(models.BalanceFlag.created_at == ts)
        .order_by(desc(models.BalanceFlag.score))
    )
    if verdict:
        stmt = stmt.where(models.BalanceFlag.verdict == verdict)

    model_bundle = supervised_model.train_hero_winrate_model(db)

    out = []
    for flag, name, image_url, role_text, playstyle, win_rate, pick_rate, kda, avg_dmg in db.execute(stmt).all():
        evidence = flag.rationale
        official_bits = []
        if role_text:
            official_bits.append(f"official role: {role_text}")
        if playstyle:
            official_bits.append(f"official playstyle: {playstyle}")
        if official_bits and "Official gameplay evidence" not in evidence:
            evidence += " Official gameplay evidence: " + " · ".join(official_bits) + "."
        ability_signal = ability_service.best_signal_for_hero(db, flag.hero_id)
        if ability_signal:
            evidence += " " + ability_signal
        elif "ability/replay telemetry" not in evidence:
            evidence += " Official ability-upgrade telemetry is not available in the stored snapshot, so this case file intentionally avoids naming a specific overpowered ability."
        stat_for_ml = db.execute(
            select(models.HeroStat)
            .where(
                (models.HeroStat.hero_id == flag.hero_id)
                & (models.HeroStat.fetched_at == ts)
            )
            .limit(1)
        ).scalar_one_or_none()
        ml_pred = supervised_model.predict_hero_baseline(model_bundle, db, stat_for_ml) if stat_for_ml else None
        ml_class = supervised_model.predict_balance_class(model_bundle, db, stat_for_ml) if stat_for_ml else None
        ml_pred, ml_gap, ml_text = _ml_recommendation_read(ml_pred, float(win_rate or 0.0), flag.verdict)
        if ml_class:
            conf = ml_class.get("confidence")
            ml_text += " ML classifier result: " + ml_class.get("label", "unknown")
            if conf is not None:
                ml_text += f" ({conf:.0%} confidence)"
            ml_text += ". This is the balance-detection classifier output, separate from the numeric win-rate regressor."
        adjusted_recommendation = _ml_adjusted_recommendation(flag.recommendation, flag.verdict, ml_gap)

        out.append(schemas.BalanceFlagOut(
            hero_id=flag.hero_id, name=name, image_url=image_url,
            verdict=flag.verdict, score=flag.score,
            rationale=evidence,
            recommendation=adjusted_recommendation,
            mechanical_reasoning=flag.mechanical_reasoning,
            macro_impact=flag.macro_impact,
            win_rate=win_rate, pick_rate=pick_rate,
            kda=kda, avg_damage=avg_dmg,
            created_at=flag.created_at,
            ml_predicted_win_rate=ml_pred,
            ml_observed_gap=ml_gap,
            ml_interpretation=ml_text,
            ml_balance_class=(ml_class.get("label") if ml_class else None),
            ml_balance_confidence=(ml_class.get("confidence") if ml_class else None),
            ml_class_probabilities=(ml_class.get("probabilities") if ml_class else None),
        ))
    return out


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    latest = db.execute(
        select(models.BalanceFlag.created_at).order_by(desc(models.BalanceFlag.created_at)).limit(1)
    ).first()
    if latest is None:
        return {"overpowered": 0, "underpowered": 0, "balanced": 0, "fetched_at": None}
    ts = latest[0]
    flags = db.execute(
        select(models.BalanceFlag.verdict).where(models.BalanceFlag.created_at == ts)
    ).scalars().all()
    counts = {"overpowered": 0, "underpowered": 0, "balanced": 0}
    for v in flags:
        counts[v] = counts.get(v, 0) + 1
    counts["fetched_at"] = ts
    return counts


@router.get("/meta-shift", response_model=schemas.MetaShiftResponse)
def meta_shift(db: Session = Depends(get_db)):
    """Compare the two most recent snapshots and show win-rate movement."""
    snaps = db.execute(
        select(models.HeroStat.fetched_at).distinct()
        .order_by(desc(models.HeroStat.fetched_at)).limit(2)
    ).scalars().all()
    if not snaps:
        return schemas.MetaShiftResponse(current_snapshot=None, previous_snapshot=None, entries=[])
    current_ts = snaps[0]
    previous_ts = snaps[1] if len(snaps) > 1 else None

    current_rows = db.execute(
        select(models.HeroStat, models.Hero.name)
        .join(models.Hero, models.Hero.id == models.HeroStat.hero_id)
        .where(models.HeroStat.fetched_at == current_ts)
    ).all()

    prev_map: dict[int, models.HeroStat] = {}
    if previous_ts is not None:
        prev_rows = db.execute(
            select(models.HeroStat).where(models.HeroStat.fetched_at == previous_ts)
        ).scalars().all()
        prev_map = {r.hero_id: r for r in prev_rows}

    entries = []
    for stat, name in current_rows:
        prev = prev_map.get(stat.hero_id)
        wr_d = (stat.win_rate - prev.win_rate) if prev else 0.0
        pr_d = (stat.pick_rate - prev.pick_rate) if prev else 0.0
        direction = "rising" if wr_d > 0.005 else "falling" if wr_d < -0.005 else "stable"
        entries.append(schemas.MetaShiftEntry(
            hero_id=stat.hero_id, name=name,
            win_rate=stat.win_rate, win_rate_delta=wr_d,
            pick_rate=stat.pick_rate, pick_rate_delta=pr_d,
            direction=direction,
        ))
    entries.sort(key=lambda e: abs(e.win_rate_delta), reverse=True)
    return schemas.MetaShiftResponse(
        current_snapshot=current_ts, previous_snapshot=previous_ts, entries=entries,
    )
