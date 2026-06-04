"""Optional ability-upgrade-path analytics.

This module only stores real upstream ability upgrade-path stats when the
Deadlock API exposes them. It does not invent ability damage, cast frequency,
or OP ability names.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .deadlock_client import DeadlockClient
from . import models


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return default


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _coerce_path_label(row: dict) -> str:
    """Build a readable label from unknown upstream ability-path shape."""
    for key in ("path", "ability_path", "skill_order", "upgrade_order", "ability_order", "order"):
        value = row.get(key)
        if isinstance(value, list):
            return " → ".join(str(v) for v in value)
        if isinstance(value, str) and value.strip():
            return value.strip()
    # Many ability pages show level/tier rows; preserve known IDs if present.
    keys = ["ability_id", "ability", "ability_name", "tier", "level", "points"]
    bits = [f"{k}:{row[k]}" for k in keys if row.get(k) not in (None, "")]
    return " · ".join(bits) if bits else "Upgrade path"


def _normalise_rows(raw: list[dict], hero_id: int | None = None) -> list[dict]:
    rows: list[dict] = []
    for row in raw or []:
        if not isinstance(row, dict):
            continue
        hid = _safe_int(row.get("hero_id") or row.get("hero") or hero_id)
        if hid <= 0:
            continue
        matches = _safe_int(row.get("matches") or row.get("match_count") or row.get("games") or row.get("sample_size"))
        wins = _safe_int(row.get("wins") or row.get("win_count"))
        wr = row.get("win_rate") or row.get("wr") or row.get("winrate")
        pr = row.get("pick_rate") or row.get("pr") or row.get("pickrate") or row.get("usage_rate")
        win_rate = _safe_float(wr, (wins / matches if matches else 0.0))
        if win_rate > 1.0:
            win_rate /= 100.0
        pick_rate = _safe_float(pr, 0.0)
        if pick_rate > 1.0:
            pick_rate /= 100.0
        item_context = row.get("item_context") or row.get("items") or row.get("item_ids")
        if isinstance(item_context, list):
            item_context = ",".join(str(i) for i in item_context)
        rows.append({
            "hero_id": hid,
            "path_label": _coerce_path_label(row)[:500],
            "matches": matches,
            "wins": wins,
            "win_rate": win_rate,
            "pick_rate": pick_rate,
            "item_context": str(item_context)[:500] if item_context not in (None, "") else None,
        })
    return rows


async def fetch_and_persist(db: Session, fetched_at: datetime, hero_ids: list[int]) -> int:
    """Fetch optional ability stats and insert rows. Returns inserted count.

    Strategy:
    1) Try global ability endpoint once.
    2) If it returns nothing, try per-hero calls for the current displayed roster.

    All failures are swallowed because ability stats are an enhancement, not a
    dependency for running the app.
    """
    client = DeadlockClient()
    inserted = 0
    try:
        raw, path = await client.ability_stats()
    except Exception:
        raw, path = [], ""
    normalised = _normalise_rows(raw)

    if not normalised:
        for hid in hero_ids[:40]:
            try:
                raw, path = await client.ability_stats(hero_id=hid)
            except Exception:
                continue
            normalised.extend(_normalise_rows(raw, hero_id=hid))

    seen = set()
    for row in normalised:
        key = (row["hero_id"], row["path_label"], row.get("item_context"))
        if key in seen:
            continue
        seen.add(key)
        if row["matches"] < 20 and row["win_rate"] <= 0:
            continue
        if db.get(models.Hero, row["hero_id"]) is None:
            continue
        db.add(models.AbilityPathStat(
            hero_id=row["hero_id"],
            fetched_at=fetched_at,
            path_label=row["path_label"],
            matches=row["matches"],
            wins=row["wins"],
            win_rate=row["win_rate"],
            pick_rate=row["pick_rate"],
            item_context=row["item_context"],
            source_note=f"Deadlock API ability upgrade-path analytics{f' ({path})' if path else ''}",
        ))
        inserted += 1
    return inserted


def latest_for_hero(db: Session, hero_id: int, limit: int = 5) -> list[models.AbilityPathStat]:
    ts = db.execute(
        select(models.AbilityPathStat.fetched_at)
        .where(models.AbilityPathStat.hero_id == hero_id)
        .order_by(desc(models.AbilityPathStat.fetched_at))
        .limit(1)
    ).scalar()
    if ts is None:
        return []
    return list(db.execute(
        select(models.AbilityPathStat)
        .where(models.AbilityPathStat.hero_id == hero_id)
        .where(models.AbilityPathStat.fetched_at == ts)
        .order_by(desc(models.AbilityPathStat.matches), desc(models.AbilityPathStat.win_rate))
        .limit(limit)
    ).scalars().all())


def best_signal_for_hero(db: Session, hero_id: int) -> str | None:
    rows = latest_for_hero(db, hero_id, limit=4)
    if not rows:
        return None
    best = sorted(rows, key=lambda r: (r.matches >= 50, r.win_rate, r.pick_rate), reverse=True)[0]
    if best.win_rate <= 0:
        return None
    return (
        f"Ability upgrade-path data available: '{best.path_label}' shows {best.win_rate:.1%} win rate"
        f" across {best.matches} matches" + (f" with {best.pick_rate:.1%} pick share" if best.pick_rate else "") +
        ". Treat this as upgrade-path evidence, not direct proof that a single ability is overpowered."
    )
