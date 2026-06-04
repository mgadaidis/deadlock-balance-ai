"""
Refresh pipeline — every external call wrapped, every count surfaced.

The response contains both upstream raw counts (`upstream_*`) and DB-side
counts (`*_inserted`), so the UI can tell the difference between
"the API gave us nothing" and "we received data but failed to persist".
"""
from __future__ import annotations

import traceback
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ability_service, items_service
from .config import settings
from .deadlock_client import DeadlockClient
from .ml.balance_analyzer import analyse_balance
from .models import BalanceFlag, Hero, HeroStat


def _safe_float(x) -> float:
    try:
        v = float(x)
        return v if np.isfinite(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _safe_int(x) -> int:
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def _text_from(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("text", "description", "value", "english", "en", "localized", "display"):
            t = value.get(key)
            if isinstance(t, str) and t.strip():
                return t.strip()
    return ""


def _hero_official_context(h: dict) -> dict[str, str]:
    desc = h.get("description") if isinstance(h.get("description"), dict) else {}
    role_text = (
        _text_from(desc.get("role")) or _text_from(h.get("role")) or
        _text_from(h.get("role_text")) or _text_from(h.get("hero_role")) or
        _text_from(h.get("class_name"))
    )
    playstyle = (
        _text_from(desc.get("playstyle")) or _text_from(h.get("playstyle")) or
        _text_from(h.get("gameplay_description")) or _text_from(h.get("short_description")) or
        _text_from(h.get("overview")) or _text_from(h.get("description"))
    )
    return {"role_text": role_text, "playstyle": playstyle}


def normalise_hero_stats(raw_stats: list[dict], heroes: list[dict]) -> pd.DataFrame:
    if not raw_stats:
        return pd.DataFrame()
    df = pd.DataFrame(raw_stats)
    rename = {
        "players_damage": "damage_sum", "damage": "damage_sum",
        "total_player_damage": "damage_sum",
        "net_worth": "networth", "max_net_worth": "networth",
        "total_net_worth": "networth",
        "total_kills": "kills", "total_deaths": "deaths", "total_assists": "assists",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    for col in ["matches", "wins", "losses", "kills", "deaths", "assists",
                "damage_sum", "networth"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["matches"] = df["matches"].where(df["matches"] > 0, df["wins"] + df["losses"])
    df["matches"] = df["matches"].astype(float)
    matches_safe = df["matches"].replace(0, np.nan)
    total_matches = float(df["matches"].sum()) or 1.0

    df["win_rate"]      = (df["wins"] / matches_safe).fillna(0.0)
    df["pick_rate"]     = (df["matches"] / total_matches).fillna(0.0)
    df["avg_kills"]     = (df["kills"] / matches_safe).fillna(0.0)
    df["avg_deaths"]    = (df["deaths"] / matches_safe).fillna(0.0)
    df["avg_assists"]   = (df["assists"] / matches_safe).fillna(0.0)
    df["kda"]           = ((df["avg_kills"] + df["avg_assists"])
                           / df["avg_deaths"].replace(0, np.nan)).fillna(
                               df["avg_kills"] + df["avg_assists"])
    df["avg_damage"]    = (df["damage_sum"] / matches_safe).fillna(0.0)
    df["avg_net_worth"] = (df["networth"]   / matches_safe).fillna(0.0)
    df["matches"]       = df["matches"].fillna(0).astype(int)

    hero_lookup = {h["id"]: h.get("name") for h in heroes if isinstance(h, dict) and "id" in h}
    hero_context = {}
    for h in heroes:
        if isinstance(h, dict) and "id" in h:
            hero_context[h["id"]] = _hero_official_context(h)
    df["name"] = df.get("hero_id", pd.Series(dtype=int)).map(hero_lookup).fillna("Unknown")
    df["role_text"] = df.get("hero_id", pd.Series(dtype=int)).map(lambda i: hero_context.get(i, {}).get("role_text", ""))
    df["playstyle"] = df.get("hero_id", pd.Series(dtype=int)).map(lambda i: hero_context.get(i, {}).get("playstyle", ""))

    if "hero_id" in df.columns:
        df["hero_id"] = pd.to_numeric(df["hero_id"], errors="coerce")
        df = df.dropna(subset=["hero_id"])
        df["hero_id"] = df["hero_id"].astype(int)
    return df


def _is_released_hero(h: dict, stat_ids: set[int] | None = None) -> bool:
    """Exclude unreleased/test heroes such as Gunslinger/Swan.

    We only display heroes that are player-selectable, not flagged as disabled or
    prerelease/testing, and present in the analytics feed. This keeps unreleased
    placeholders out of the UI without hardcoding names.
    """
    try:
        hid = int(h.get("id"))
    except (TypeError, ValueError):
        return False
    if stat_ids is not None and hid not in stat_ids:
        return False
    if h.get("disabled") or h.get("in_development") or h.get("prerelease_only") or h.get("limited_testing"):
        return False
    if h.get("player_selectable") is False:
        return False
    if h.get("assigned_players_only") is True or h.get("needs_testing") is True:
        return False
    return True


def _ingest_heroes(db: Session, heroes_raw: list[dict], stat_ids: set[int] | None = None) -> int:
    loaded = 0
    for h in heroes_raw or []:
        if not isinstance(h, dict) or "id" not in h or not h.get("name"):
            continue
        if not _is_released_hero(h, stat_ids=stat_ids):
            continue
        hero = db.get(Hero, h["id"])
        image_url = None
        imgs = h.get("images")
        if isinstance(imgs, dict):
            image_url = (
                imgs.get("icon_image_small_webp") or imgs.get("icon_image_small")
                or imgs.get("icon_hero_card_webp") or imgs.get("icon_hero_card")
                or imgs.get("portrait")
                or next((v for v in imgs.values() if isinstance(v, str)), None)
            )
        ctx = _hero_official_context(h)
        role_text = ctx.get("role_text") or None
        playstyle = ctx.get("playstyle") or None
        role = h.get("hero_type") or h.get("type") if isinstance((h.get("hero_type") or h.get("type")), str) else None
        if hero is None:
            hero = Hero(id=h["id"], name=h["name"], role=role, image_url=image_url, role_text=role_text, playstyle=playstyle)
            db.add(hero)
        else:
            hero.name = h["name"]
            hero.role = role or hero.role
            hero.image_url = image_url or hero.image_url
            hero.role_text = role_text or hero.role_text
            hero.playstyle = playstyle or hero.playstyle
        loaded += 1
    db.flush()
    return loaded


def _insert_hero_stats(db: Session, df: pd.DataFrame, fetched_at: datetime) -> int:
    inserted = 0
    for _, row in df.iterrows():
        hero_id = _safe_int(row.get("hero_id"))
        if hero_id == 0 or db.get(Hero, hero_id) is None:
            continue
        db.add(HeroStat(
            hero_id=hero_id, fetched_at=fetched_at,
            matches=_safe_int(row.get("matches")),
            wins=_safe_int(row.get("wins")),
            losses=_safe_int(row.get("losses")),
            win_rate=_safe_float(row.get("win_rate")),
            pick_rate=_safe_float(row.get("pick_rate")),
            avg_kills=_safe_float(row.get("avg_kills")),
            avg_deaths=_safe_float(row.get("avg_deaths")),
            avg_assists=_safe_float(row.get("avg_assists")),
            kda=_safe_float(row.get("kda")),
            avg_damage=_safe_float(row.get("avg_damage")),
            avg_net_worth=_safe_float(row.get("avg_net_worth")),
        ))
        inserted += 1
    return inserted


def _insert_flags(db: Session, flags: list[dict], fetched_at: datetime) -> int:
    inserted = 0
    for f in flags or []:
        db.add(BalanceFlag(
            hero_id=f["hero_id"], created_at=fetched_at,
            verdict=f["verdict"], score=f["score"],
            rationale=f["rationale"],
            recommendation=f["recommendation"],
            mechanical_reasoning=f.get("mechanical_reasoning", ""),
            macro_impact=f.get("macro_impact", ""),
        ))
        inserted += 1
    return inserted


async def refresh_all(db: Session) -> dict:
    client = DeadlockClient()
    fetched_at = datetime.utcnow()
    errors: list[str] = []

    # ---- heroes + hero stats ----
    heroes_raw: list[dict] = []
    try:
        heroes_raw = await client.heroes()
    except Exception as e:
        errors.append(f"heroes fetch failed: {e!s}")
        traceback.print_exc()
    upstream_heroes = len(heroes_raw)

    stats_raw: list[dict] = []
    mode_used: str = ""
    try:
        stats_raw, mode_used = await client.hero_stats()
    except Exception as e:
        errors.append(f"hero-stats fetch failed: {e!s}")
        traceback.print_exc()
    upstream_stats = len(stats_raw)

    stat_ids = { _safe_int(s.get("hero_id")) for s in stats_raw if isinstance(s, dict) and _safe_int(s.get("matches")) > 0 }

    heroes_loaded = 0
    try:
        heroes_loaded = _ingest_heroes(db, heroes_raw, stat_ids=stat_ids)
        db.commit()
    except Exception as e:
        errors.append(f"hero ingest failed: {e!s}")
        traceback.print_exc()
        db.rollback()

    # If we asked for a mode filter but the upstream silently returned the
    # unfiltered set, tell the user. They'll see why their "Normal mode only"
    # request gave them everything.
    if settings.match_mode and not mode_used and stats_raw:
        errors.append(
            f"mode filter '{settings.match_mode}' was not accepted by any of the "
            f"upstream parameter names tried — falling back to unfiltered data. "
            f"Set MATCH_MODE in .env to '' to silence this notice."
        )

    stats_inserted = 0
    flags_generated = 0
    if stats_raw:
        try:
            df = normalise_hero_stats(stats_raw, heroes_raw)
            stats_inserted = _insert_hero_stats(db, df, fetched_at)
            # Analyse only heroes that were actually ingested/displayable.
            df = df[df["hero_id"].apply(lambda x: db.get(Hero, _safe_int(x)) is not None)]
            flags = analyse_balance(df)
            flags_generated = _insert_flags(db, flags, fetched_at)
            db.commit()
        except Exception as e:
            errors.append(f"hero stats/analysis failed: {e!s}")
            traceback.print_exc()
            db.rollback()

    # ---- items (optional) ----
    items_inserted = 0
    try:
        items_inserted = await items_service.fetch_and_persist(db, fetched_at)
        db.commit()
    except Exception as e:
        errors.append(f"items fetch/persist failed: {e!s}")
        traceback.print_exc()
        db.rollback()

    # ---- ability upgrade paths (optional enhancement) ----
    ability_paths_inserted = 0
    try:
        displayable_hero_ids = list(db.execute(select(Hero.id).order_by(Hero.name)).scalars().all())
        ability_paths_inserted = await ability_service.fetch_and_persist(db, fetched_at, displayable_hero_ids)
        if ability_paths_inserted == 0:
            errors.append(
                "ability upgrade-path endpoint returned no usable rows; recommendations remain based on hero/item aggregates only."
            )
        db.commit()
    except Exception as e:
        errors.append(f"ability stats fetch/persist failed: {e!s}")
        traceback.print_exc()
        db.rollback()

    # Each stage commits independently above. If one optional stage fails, earlier
    # successful data still remains visible instead of the whole refresh being
    # rolled back.

    return {
        "heroes_loaded": heroes_loaded,
        "stats_inserted": stats_inserted,
        "items_inserted": items_inserted,
        "flags_generated": flags_generated,
        "fetched_at": fetched_at,
        "match_mode": settings.match_mode or "",
        "mode_param_used": mode_used,
        "upstream_heroes": upstream_heroes,
        "upstream_stats": upstream_stats,
        "errors": errors,
        "ability_paths_inserted": ability_paths_inserted,
    }
