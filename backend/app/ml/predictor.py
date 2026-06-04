"""
Phase-by-phase match simulator.

The simulator uses real hero/item aggregate stats. Item builds are applied per
hero. Build value is NOT just item win rate: it combines global item quality,
confidence, category fit, hero profile, build completeness, and optional ability
upgrade-path signals when the upstream endpoint provides them.

Limitations stay explicit: without true hero-item pair rows or replay logs, this
is a transparent heuristic, not a professional matchmaker model.
"""
from __future__ import annotations

import math
from statistics import median
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .. import ability_service, models
from ..data.hero_archetypes import affinity_for
from . import supervised_model

SENSITIVITY = 4.8

WEAPON_WORDS = {
    "bullet", "magazine", "ammo", "headshot", "sharpshooter", "tesla", "burst", "rapid", "reload",
    "gun", "shot", "shots", "fire", "kinetic", "long range", "point blank", "slowing bullets", "toxic bullets",
}
SPIRIT_WORDS = {
    "spirit", "mystic", "arcane", "boundless", "improved spirit", "surge", "duration", "cooldown",
    "recharge", "curse", "hex", "torment", "alchemical", "echo", "expansion", "burst", "shredder",
}
VITALITY_WORDS = {
    "health", "armor", "barrier", "shield", "regen", "stamina", "lifesteal", "rescue", "fortitude",
    "enduring", "healing", "debuff reducer", "reactive", "restorative", "spirit shielding", "bullet armor",
}


def _latest_snapshot(db: Session):
    return db.execute(select(models.HeroStat.fetched_at).order_by(desc(models.HeroStat.fetched_at)).limit(1)).scalar()


def _latest_stat(db: Session, hero_id: int) -> models.HeroStat | None:
    return db.execute(
        select(models.HeroStat).where(models.HeroStat.hero_id == hero_id).order_by(desc(models.HeroStat.fetched_at)).limit(1)
    ).scalars().first()


def _hero(db: Session, hero_id: int) -> models.Hero | None:
    return db.get(models.Hero, hero_id)


def _hero_name(db: Session, hero_id: int) -> str:
    h = _hero(db, hero_id)
    return h.name if h else f"Hero #{hero_id}"


def _avg(values: list[float], default: float = 0.0) -> float:
    return sum(values) / len(values) if values else default


def _bound(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _baselines(db: Session) -> dict[str, float]:
    ts = _latest_snapshot(db)
    if ts is None:
        return {"damage": 18000.0, "deaths": 6.0, "kda": 3.0, "net": 25000.0, "wr": 0.5}
    rows = db.execute(select(models.HeroStat).where(models.HeroStat.fetched_at == ts)).scalars().all()
    if not rows:
        return {"damage": 18000.0, "deaths": 6.0, "kda": 3.0, "net": 25000.0, "wr": 0.5}
    return {
        "damage": float(median([r.avg_damage for r in rows if r.avg_damage is not None] or [18000.0])),
        "deaths": float(median([r.avg_deaths for r in rows if r.avg_deaths is not None] or [6.0])),
        "kda": float(median([r.kda for r in rows if r.kda is not None] or [3.0])),
        "net": float(median([r.avg_net_worth for r in rows if r.avg_net_worth is not None] or [25000.0])),
        "wr": float(median([r.win_rate for r in rows if r.win_rate is not None] or [0.5])),
    }


def _item_row(db: Session, item_id: int) -> models.ItemStat | None:
    return db.execute(
        select(models.ItemStat).where(models.ItemStat.item_id == item_id).order_by(desc(models.ItemStat.fetched_at)).limit(1)
    ).scalars().first()


def _category(item: models.ItemStat | None) -> str:
    if item is None:
        return "unknown"
    raw = ((item.category or "") + " " + (item.name or "")).lower()
    if any(w in raw for w in WEAPON_WORDS) or "weapon" in raw:
        return "weapon"
    if any(w in raw for w in SPIRIT_WORDS) or "spirit" in raw:
        return "spirit"
    if any(w in raw for w in VITALITY_WORDS) or "vital" in raw:
        return "vitality"
    return "unknown"


def _hero_affinity(db: Session, stat: models.HeroStat, base: dict[str, float]) -> dict[str, float]:
    """Derived role affinity from stats + official text when available."""
    dmg = (stat.avg_damage - base["damage"]) / max(base["damage"], 1)
    net = (stat.avg_net_worth - base["net"]) / max(base["net"], 1)
    deaths = (stat.avg_deaths - base["deaths"]) / max(base["deaths"], 1)
    kda = (stat.kda - base["kda"]) / max(base["kda"], 1)
    text = ""
    h = _hero(db, stat.hero_id)
    if h:
        text = f"{h.role or ''} {h.role_text or ''} {h.playstyle or ''}".lower()

    weapon = 1.00 + _bound(dmg * 0.60 + kda * 0.25, -0.35, 0.35)
    spirit = 1.00 + _bound(dmg * 0.45 + net * 0.40, -0.35, 0.35)
    vitality = 1.00 + _bound(deaths * 0.75 - kda * 0.20, -0.35, 0.40)

    # Official text nudges only when it clearly describes playstyle. It never
    # overrides the numeric profile by itself.
    if any(w in text for w in ("spirit", "spell", "ability", "mystic", "curse", "turret", "zone", "area")):
        spirit += 0.18
    if any(w in text for w in ("gun", "weapon", "bullet", "marksman", "precise", "shoot")):
        weapon += 0.18
    if any(w in text for w in ("tank", "front", "survive", "sustain", "support", "shield", "healing")):
        vitality += 0.18

    # Bundled archetype affinity (gathered outside the analytics API because the
    # API exposes no hero-item pair data). It is blended in, not substituted, so
    # the live numeric profile still leads; an unknown hero changes nothing.
    arche = affinity_for(h.name) if h else None
    if arche:
        weapon = weapon * 0.6 + arche["weapon"] * 0.4
        spirit = spirit * 0.6 + arche["spirit"] * 0.4
        vitality = vitality * 0.6 + arche["vitality"] * 0.4

    return {
        "weapon": _bound(weapon, 0.65, 1.45),
        "spirit": _bound(spirit, 0.65, 1.45),
        "vitality": _bound(vitality, 0.65, 1.50),
        "unknown": 0.78,
    }


def _tier_component(item: models.ItemStat | None) -> float:
    if item is None:
        return -0.010
    # Global item quality.  This is deliberately stronger than before so
    # intentionally awful builds can hurt and coherent builds can help.
    wr_component = _bound((float(item.win_rate) - 0.5) * 1.25, -0.075, 0.075)
    conf = max(0.35, min(1.0, float(item.confidence or 0.35)))
    tier_bias = {"S": 0.020, "A": 0.012, "B": 0.004, "C": -0.010, "D": -0.025}.get((item.tier or "C").upper(), 0.0)
    return (wr_component * conf) + tier_bias


def _build_bonus_for_hero(db: Session, stat: models.HeroStat, item_ids: list[int] | None, base: dict[str, float]) -> tuple[float, list[str], float]:
    """Return (build_bonus, notes, compatibility).

    ``compatibility`` is a 0..1 measure of how well the chosen item categories
    suit this hero, independent of raw item win rate. It is what makes the
    result reflect *build fit* and not only win rates.
    """
    name = _hero_name(db, stat.hero_id)
    if not item_ids:
        return 0.0, [f"{name} has no assigned items; simulator uses the supervised ML hero baseline and applies neutral build impact with lower build-specific confidence."], 0.5

    aff = _hero_affinity(db, stat, base)
    total = 0.0
    notes = []
    seen_categories: dict[str, int] = {}
    compat_samples: list[float] = []
    for iid in item_ids[:12]:
        item = _item_row(db, iid)
        if item is None:
            total -= 0.01
            continue
        cat = _category(item)
        seen_categories[cat] = seen_categories.get(cat, 0) + 1
        compatibility = aff.get(cat, aff["unknown"])
        compat_samples.append(compatibility)
        raw = _tier_component(item)
        # Bad, incompatible items should actively hurt. Good compatible items
        # should matter enough to move a simulation result.
        contribution = raw * compatibility
        if cat != "unknown" and compatibility < 0.82 and raw > 0:
            contribution *= 0.25
            contribution -= 0.012
        if item.tier in ("C", "D") and compatibility < 1.05:
            contribution -= 0.010
        total += contribution
        if compatibility >= 1.15:
            fit = "strong fit"
        elif compatibility <= 0.85:
            fit = "weak fit"
        else:
            fit = "neutral fit"
        notes.append(
            f"{name} + {item.name}: {fit} for {cat} profile; item WR {item.win_rate:.1%}, confidence {item.confidence:.2f}."
        )

    # Build coherence bonus/penalty: coherent builds are rewarded, random mixed
    # baskets are not. This helps a correct spirit-style build beat a
    # deliberately bad weapon build instead of everything collapsing to hero WR.
    dominant_cat, dominant_count = max(seen_categories.items(), key=lambda kv: kv[1]) if seen_categories else ("unknown", 0)
    if dominant_cat != "unknown" and dominant_count >= 6 and aff.get(dominant_cat, 0.8) >= 1.05:
        total += 0.07
        notes.append(f"{name}'s build is coherent: {dominant_count} selected items reinforce the {dominant_cat} profile.")
    elif dominant_count <= 3 and len(item_ids) >= 8:
        total -= 0.045
        notes.append(f"{name}'s build is scattered across categories, so item value is discounted.")

    # Optional ability upgrade-path signal when stored. It only nudges, because
    # we do not know whether the user selected that exact path in the simulator.
    ability_signal = ability_service.best_signal_for_hero(db, stat.hero_id)
    if ability_signal:
        rows = ability_service.latest_for_hero(db, stat.hero_id, limit=1)
        if rows:
            total += _bound((rows[0].win_rate - stat.win_rate) * 0.40, -0.035, 0.045)
        notes.append(ability_signal)

    # Completion curve: a full 12-item build should carry far more weight than a
    # single accidental S-tier item. Past 12 there is no further slot to fill.
    completion = min(len(item_ids), 12) / 12
    total *= (0.45 + 0.55 * completion)

    # Compatibility score: map the average category fit (~0.65..1.45, centred on
    # 1.0) onto 0..1. A coherent dominant category lifts it slightly.
    avg_compat = _avg(compat_samples, 1.0)
    compat_score = _bound((avg_compat - 0.65) / 0.8, 0.0, 1.0)
    if dominant_cat != "unknown" and dominant_count >= 6 and aff.get(dominant_cat, 0.8) >= 1.05:
        compat_score = min(1.0, compat_score + 0.08)
    return _bound(total, -0.28, 0.28), notes[:6], compat_score


def _team_item_bonus(db: Session, team: list[models.HeroStat], builds: dict | None, fallback_ids: list[int] | None, base: dict[str, float]) -> tuple[float, list[str], float]:
    """Return (avg_build_bonus, notes, avg_compatibility) for a whole team."""
    if not team:
        return 0.0, [], 0.5
    bonuses, notes, compats = [], [], []
    builds = builds or {}
    for stat in team:
        hero_items = None
        if builds:
            hero_items = builds.get(str(stat.hero_id)) or builds.get(stat.hero_id)
        if hero_items is None:
            hero_items = fallback_ids
        b, n, c = _build_bonus_for_hero(db, stat, hero_items, base)
        bonuses.append(b)
        compats.append(c)
        notes.extend(n[:3])
    return _bound(_avg(bonuses, 0.0), -0.28, 0.28), notes[:12], _avg(compats, 0.5)


def _phase_early(team: list[models.HeroStat], enemy: list[models.HeroStat], team_item_bonus: float, enemy_item_bonus: float) -> tuple[float, str, list[str]]:
    t_kda, e_kda = _avg([s.kda for s in team], 3.0), _avg([s.kda for s in enemy], 3.0)
    t_dth, e_dth = _avg([s.avg_deaths for s in team], 6.0), _avg([s.avg_deaths for s in enemy], 6.0)
    item_delta = team_item_bonus - enemy_item_bonus
    adv = _bound((t_kda - e_kda) * 0.07 + (e_dth - t_dth) * 0.04 + item_delta * 0.55)
    if adv > 0.15:
        return adv, "Lanes lean your way.", [
            f"Team enters lane with KDA {t_kda:.2f} vs {e_kda:.2f}.",
            f"Build setup already adds {item_delta:+.2f} relative advantage before mid-game scaling.",
            "First rotations should be playable if lanes avoid unnecessary deaths.",
        ]
    if adv < -0.15:
        return adv, "Enemy controls the lanes.", [
            f"Enemy KDA profile ({e_kda:.2f}) and/or build setup outclasses your laners ({t_kda:.2f}).",
            f"Build setup delta is {item_delta:+.2f}; early fights are risky.",
            "Play defensive waves and avoid forced skirmishes until item timings improve.",
        ]
    return adv, "Laning phase even.", ["Lane KDA and item setup are close enough that no side has a clear early read."]


def _phase_mid(team: list[models.HeroStat], enemy: list[models.HeroStat], team_item_bonus: float, enemy_item_bonus: float) -> tuple[float, str, list[str]]:
    t_dmg, e_dmg = _avg([s.avg_damage for s in team], 18000), _avg([s.avg_damage for s in enemy], 18000)
    t_nw, e_nw = _avg([s.avg_net_worth for s in team], 25000), _avg([s.avg_net_worth for s in enemy], 25000)
    item_delta = team_item_bonus - enemy_item_bonus
    adv = _bound((t_dmg - e_dmg) / 14000 * 0.30 + (t_nw - e_nw) / 20000 * 0.22 + item_delta * 1.25)
    if adv > 0.15:
        return adv, "Mid-game spikes favour your team.", [
            f"Damage profile {t_dmg:.0f} vs {e_dmg:.0f}; build compatibility delta {item_delta:+.2f} amplifies the timing.",
            f"Net-worth delta of ~{int(t_nw - e_nw):+} souls affects tier timing.",
            "Contest urn and guardian windows while selected builds are ahead.",
        ]
    if adv < -0.15:
        return adv, "Enemy out-scales the mid game.", [
            f"Enemy damage profile ({e_dmg:.0f}) and/or build quality outpaces yours ({t_dmg:.0f}).",
            f"Build compatibility delta is {item_delta:+.2f}; avoid direct 6v6 fights.",
            "Play around picks, split waves, and delay until better item completion.",
        ]
    return adv, "Mid game stays close.", ["Damage, economy, and selected item builds remain within striking distance."]


def _phase_late(team: list[models.HeroStat], enemy: list[models.HeroStat], team_item_bonus: float, enemy_item_bonus: float) -> tuple[float, str, list[str]]:
    t_wr, e_wr = _avg([s.win_rate for s in team], 0.5), _avg([s.win_rate for s in enemy], 0.5)
    item_delta = team_item_bonus - enemy_item_bonus
    # Hero win-rate still matters, but selected builds now matter more than the
    # previous version, because the user is explicitly simulating builds.
    adv = _bound((t_wr - e_wr) * 2.2 + item_delta * 2.35)
    item_line = f"Item/build compatibility delta {item_delta:+.2f} after category-fit and coherence adjustment."
    if adv > 0.15:
        return adv, "Late-game composition favours your side.", [
            f"Composite WR profile ({t_wr:.1%} vs {e_wr:.1%}) plus builds gives your draft the long-game edge.",
            item_line,
            "Force a coordinated Patron fight once core builds are online.",
        ]
    if adv < -0.15:
        return adv, "Enemy is favoured at full build.", [
            f"Enemy composite WR ({e_wr:.1%}) and/or build fit outpaces yours ({t_wr:.1%}).",
            item_line,
            "Close tempo earlier or avoid equal full-build fights.",
        ]
    return adv, "Late game is close.", ["Composite win-rate and item-fit profiles are almost tied.", item_line]


def simulate(db: Session, hero_ids: list[int], enemy_ids: list[int] | None, team_item_ids: list[int] | None, enemy_item_ids: list[int] | None, team_hero_item_builds: dict | None = None, enemy_hero_item_builds: dict | None = None) -> dict:
    team = [s for s in (_latest_stat(db, h) for h in hero_ids) if s is not None]
    if not team:
        return {
            "win_probability": 0.5,
            "team_avg_win_rate": 0.5,
            "enemy_avg_win_rate": None,
            "phases": [],
            "summary": "No stats available for the selected heroes — refresh data first.",
            "item_analysis": [],
            "model_note": "No simulation could be produced because selected heroes have no stored stats.",
        }
    enemy = [s for s in (_latest_stat(db, h) for h in (enemy_ids or [])) if s is not None]
    base = _baselines(db)
    team_item_bonus, team_notes, team_compat = _team_item_bonus(db, team, team_hero_item_builds, team_item_ids, base)
    enemy_item_bonus, enemy_notes, enemy_compat = _team_item_bonus(db, enemy, enemy_hero_item_builds, enemy_item_ids, base)

    # Real supervised ML layer: train a RandomForestRegressor on the latest
    # hero snapshot and use it as an additional baseline signal.  The target is
    # hero win rate; features exclude win rate itself and include KDA, damage,
    # deaths, assists, economy, pick rate, sample size, and role.
    ml_bundle = supervised_model.train_hero_winrate_model(db)
    team_ml_avg, team_ml_notes = supervised_model.predict_team_baseline(ml_bundle, db, team)
    enemy_ml_avg, enemy_ml_notes = supervised_model.predict_team_baseline(ml_bundle, db, enemy)

    e_adv, e_head, e_events = _phase_early(team, enemy, team_item_bonus, enemy_item_bonus)
    m_adv, m_head, m_events = _phase_mid(team, enemy, team_item_bonus, enemy_item_bonus)
    l_adv, l_head, l_events = _phase_late(team, enemy, team_item_bonus, enemy_item_bonus)

    # Draft baseline is intentionally modest; otherwise a low-WR hero can never
    # overcome a high-WR opponent even with a much better build.
    team_avg = _avg([s.win_rate for s in team])
    enemy_avg = _avg([s.win_rate for s in enemy]) if enemy else base["wr"]
    draft_delta = _bound((team_avg - enemy_avg) * 1.35, -0.18, 0.18)

    # Build-compatibility term: a dedicated, win-rate-independent contribution so
    # the outcome tracks how well each build fits its hero, not only hero win
    # rates. Enemy compatibility defaults to a neutral 0.5 when no enemy build is
    # supplied, so a strong team build is still rewarded.
    enemy_fit_ref = enemy_compat if enemy else 0.5
    compat_delta = _bound((team_compat - enemy_fit_ref) * 0.6, -0.30, 0.30)

    # ML contribution.  If no enemy team is selected, compare the team to the
    # lobby baseline.  The term is capped so the trained model informs the
    # simulator without hiding the transparent phase/build reasoning.
    if team_ml_avg is not None:
        enemy_ml_ref = enemy_ml_avg if enemy_ml_avg is not None else base["wr"]
        ml_delta = _bound((team_ml_avg - enemy_ml_ref) * 2.0, -0.24, 0.24)
    else:
        ml_delta = 0.0

    overall = (
        draft_delta * 0.12
        + e_adv * 0.16
        + m_adv * 0.25
        + l_adv * 0.18
        + compat_delta * 0.19
        + ml_delta * 0.10
    )
    win_prob = 1.0 / (1.0 + math.exp(-SENSITIVITY * overall))
    enemy_avg_out = _avg([s.win_rate for s in enemy]) if enemy else None

    summary = (
        f"Composite advantage {overall:+.2f} → win probability {win_prob:.1%}. "
        f"Draft baseline {draft_delta:+.2f} · Early {e_adv:+.2f} · Mid {m_adv:+.2f} · Late {l_adv:+.2f} · "
        f"Build fit {compat_delta:+.2f} · ML baseline {ml_delta:+.2f}. "
        f"Your build compatibility is {team_compat*100:.0f}%"
        + (f" vs the enemy's {enemy_compat*100:.0f}%" if enemy else "")
        + ". Build fit is weighted independently of win rate, so an incompatible build lowers the result even on a strong hero."
    )

    if ml_bundle is not None:
        model_note = (
            f"Supervised ML active: RandomForestRegressor + RandomForestClassifier trained on {ml_bundle.rows} latest hero rows"
            + (f"; regression MAE ≈ {ml_bundle.mae:.1%}" if ml_bundle.mae is not None else "")
            + (f"; classifier accuracy ≈ {ml_bundle.classifier_accuracy:.0%}. " if getattr(ml_bundle, 'classifier_accuracy', None) is not None else ". ")
            + "The regressor predicts baseline win rate, and the classifier predicts balance class from KDA, damage, economy, pick rate, sample size, deaths and role. "
            + "Selected items adjust the result through an explainable build-fit layer because the public data does not expose full labeled hero-item match rows."
        )
    else:
        model_note = (
            "Supervised ML unavailable: not enough refreshed hero rows were available to train the RandomForestRegressor. "
            "Run Refresh Data first. Until then, the simulator uses the explainable scoring model only."
        )

    return {
        "win_probability": win_prob,
        "team_avg_win_rate": team_avg,
        "enemy_avg_win_rate": enemy_avg_out,
        "team_build_compatibility": team_compat,
        "enemy_build_compatibility": enemy_compat if enemy else None,
        "phases": [
            {"phase": "early", "time_range": "0–10 min", "team_advantage": e_adv, "headline": e_head, "events": e_events},
            {"phase": "mid", "time_range": "10–25 min", "team_advantage": m_adv, "headline": m_head, "events": m_events},
            {"phase": "late", "time_range": "25 min+", "team_advantage": l_adv, "headline": l_head, "events": l_events},
        ],
        "summary": summary,
        "item_analysis": (
            team_notes
            + (["ML hero baseline notes:"] + team_ml_notes if team_ml_notes else [])
            + (["Enemy build notes:"] + enemy_notes if enemy_notes else [])
            + (["Enemy ML baseline notes:"] + enemy_ml_notes if enemy_ml_notes else [])
        ),
        "model_note": model_note,
    }
