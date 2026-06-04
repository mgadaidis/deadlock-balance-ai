"""
Standalone items module — all item-related logic lives here.

This module is the single source of truth for:
  * Fetching item metadata from the assets API
  * Fetching item analytics from the analytics API
  * Normalising item stats and computing tier rankings (S/A/B/C/D)
  * Querying stored item stats from the DB

It exposes a small surface (`build_item_stats`, `tier_for`, `latest_item_stats`)
that the data pipeline and routers call. Nothing else in the app should
reach into raw item payloads directly — they go through this module.
"""
from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from . import models
from .data import item_relations
from .deadlock_client import DeadlockClient


# ---- tier thresholds (data-driven, see compute_tiers) ----
TIER_BOUNDS = {
    "S": 0.555,
    "A": 0.530,
    "B": 0.500,
    "C": 0.470,
}


def tier_for(win_rate: float) -> str:
    """Map a win rate to a tier letter using shared thresholds."""
    if win_rate >= TIER_BOUNDS["S"]:
        return "S"
    if win_rate >= TIER_BOUNDS["A"]:
        return "A"
    if win_rate >= TIER_BOUNDS["B"]:
        return "B"
    if win_rate >= TIER_BOUNDS["C"]:
        return "C"
    return "D"


def _pick_icon(it: dict) -> str | None:
    """Return a consistent official in-game item artwork URL.

    The assets API can expose several images per item. To avoid a mixed look
    (some small symbolic icons, some store art, some placeholders), we prefer
    the in-game shop/upgrade artwork first. We still never invent filenames:
    only URLs already supplied by the upstream assets metadata are used.
    """
    candidates: list[str] = []

    def add(v):
        if isinstance(v, str) and v:
            candidates.append(v)

    imgs = it.get("images")
    if isinstance(imgs, dict):
        # Highest priority: in-game shop/upgrade card artwork.
        for key in (
            "shop_image_webp", "shop_image",
            "upgrade_image_webp", "upgrade_image",
            "item_image_webp", "item_image",
            "image_webp", "image",
            # Fallback official icons only if card artwork is absent.
            "icon_webp", "icon",
        ):
            add(imgs.get(key))

    for key in (
        "shop_image_webp", "shop_image",
        "upgrade_image_webp", "upgrade_image",
        "item_image_webp", "item_image",
        "image_url", "image",
        "icon_url", "icon",
    ):
        add(it.get(key))

    # Prefer the official assets bucket / deadlock-api URLs. Do not generate
    # random placeholders; if no official URL exists, return None and the
    # frontend simply omits the image.
    for v in candidates:
        if v.startswith("http") and ("deadlock-api.com" in v or "assets-bucket" in v):
            return v
    return next((v for v in candidates if v.startswith("http")), None)


def _extract_relation_ids(it: dict) -> list[int]:
    """Pull any component/upgrade item ids the upstream metadata exposes.

    Field names vary across Deadlock API releases, so we try several and accept
    whatever is present. Missing data is fine — the name-based fallback in
    ``compute_exclusivity`` still groups upgrade variants.
    """
    out: list[int] = []
    for key in (
        "component_items", "components", "upgrade_items", "upgrades",
        "tier_upgrade", "parent_item", "base_item", "upgrade_item_id",
        "child_items", "required_items",
    ):
        val = it.get(key)
        if val is None:
            continue
        candidates = val if isinstance(val, list) else [val]
        for c in candidates:
            if isinstance(c, dict):
                c = c.get("id") or c.get("item_id")
            try:
                out.append(int(c))
            except (TypeError, ValueError):
                continue
    return out


def _normalise_item_meta(items_raw: list[dict]) -> dict[int, dict]:
    """Index items metadata by id; pull name + category + tier slot + icon."""
    out: dict[int, dict] = {}
    for it in items_raw or []:
        if not isinstance(it, dict):
            continue
        raw_id = it.get("id") or it.get("item_id")
        if raw_id is None:
            continue
        # Different endpoints expose different field names; we coalesce.
        name = (
            it.get("name_localized") or it.get("name") or it.get("display_name")
            or it.get("item_name") or f"Item #{raw_id}"
        )
        category = (
            it.get("item_slot_type") or it.get("slot_type") or it.get("type")
            or it.get("slot") or it.get("category") or ""
        ).lower()
        try:
            tier_slot = int(it.get("item_tier") or it.get("tier") or it.get("tier_slot") or 0)
        except (TypeError, ValueError):
            tier_slot = 0
        out[int(raw_id)] = {
            "name": str(name),
            "category": str(category),
            "tier_slot": tier_slot,
            "icon_url": _pick_icon(it),
            "relation_ids": _extract_relation_ids(it),
        }
    return out


def compute_exclusivity(df: pd.DataFrame, meta: dict[int, dict]) -> dict[int, dict]:
    """Build direct item upgrade exclusions for the simulator.

    Important behaviour:
    - A base item blocks each direct upgrade.
    - A direct upgrade blocks its base item.
    - Sibling upgrades do NOT block each other.

    Example from item_upgrade_paths.json:
      Rapid Rounds -> Burst Fire / Swift Striker

    If Swift Striker is selected, Rapid Rounds is disabled, but Burst Fire
    remains selectable because it is a sibling upgrade, not the same direct item.
    """
    present_ids = {int(i) for i in df["item_id"].tolist()}
    id_to_name = {int(r["item_id"]): str(r["name"]) for _, r in df.iterrows()}
    name_to_id = {item_relations._norm(v): k for k, v in id_to_name.items()}

    out: dict[int, dict] = {iid: {"group_key": None, "exclusive_ids": []} for iid in present_ids}
    labels: dict[int, list[str]] = {iid: [] for iid in present_ids}

    def add_edge(a: int, b: int, label: str) -> None:
        if a not in present_ids or b not in present_ids or a == b:
            return
        for src, dst in ((a, b), (b, a)):
            ids = out[src].setdefault("exclusive_ids", [])
            if dst not in ids:
                ids.append(dst)
            if label not in labels[src]:
                labels[src].append(label)

    # 1) Direct relationships from the editable JSON data file.
    # We intentionally prefer the project data file over ambiguous upstream
    # relation arrays, because some APIs expose a whole upgrade family instead
    # of direct parent-child edges. Whole-family data would incorrectly make
    # sibling upgrades block each other.
    for edge in item_relations.curated_edges():
        base_id = name_to_id.get(edge["base"])
        up_id = name_to_id.get(edge["upgrade"])
        if base_id and up_id:
            add_edge(base_id, up_id, edge.get("label") or "upgrade")

    # 2) Keep a very conservative same-stem fallback only for two-item pairs.
    # This catches simple "Basic X -> Improved X" style metadata gaps without
    # recreating the old sibling-clique bug.
    stem_buckets: dict[str, list[int]] = {}
    for iid in present_ids:
        stem = item_relations.family_stem(id_to_name[iid])
        if stem:
            stem_buckets.setdefault(stem, []).append(iid)
    for stem, ids in stem_buckets.items():
        if len(ids) == 2:
            add_edge(ids[0], ids[1], f"stem:{stem}")

    for iid in present_ids:
        out[iid]["exclusive_ids"] = sorted(set(int(x) for x in out[iid].get("exclusive_ids", [])))
        out[iid]["group_key"] = " | ".join(labels[iid])[:96] if labels[iid] else None
    return out


def build_item_stats(items_meta_raw: list[dict], item_stats_raw: list[dict]) -> pd.DataFrame:
    """
    Merge metadata + analytics into a single DataFrame ready for insertion.
    Columns: item_id, name, category, tier_slot, matches, wins, win_rate,
    confidence, tier, group_key, exclusive_ids.
    """
    if not item_stats_raw:
        return pd.DataFrame()

    df = pd.DataFrame(item_stats_raw)
    # Coalesce a few possible field names from the upstream
    rename = {"item": "item_id"}
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    for col in ["item_id", "matches", "wins"]:
        if col not in df.columns:
            df[col] = 0

    df["matches"] = pd.to_numeric(df["matches"], errors="coerce").fillna(0)
    df["wins"] = pd.to_numeric(df["wins"], errors="coerce").fillna(0)

    # Win rate, with NaN on zero-match items
    df["win_rate"] = np.where(df["matches"] > 0, df["wins"] / df["matches"], np.nan)

    # Confidence = log-scaled sample size, clipped to [0, 1]
    # log10(matches) / log10(50000) gives ~0 at small N and ~1 at large N.
    df["confidence"] = np.clip(np.log10(df["matches"].clip(lower=1)) / np.log10(50000), 0.0, 1.0)

    # Drop items with no observed games — they pollute the tier list
    df = df.dropna(subset=["win_rate"])
    df = df[df["matches"] >= 100].reset_index(drop=True)

    # Attach metadata
    meta = _normalise_item_meta(items_meta_raw)
    df["name"] = df["item_id"].map(lambda i: meta.get(int(i), {}).get("name", f"Item #{int(i)}"))
    df["category"] = df["item_id"].map(lambda i: meta.get(int(i), {}).get("category", ""))
    df["tier_slot"] = df["item_id"].map(lambda i: meta.get(int(i), {}).get("tier_slot", 0)).astype(int)
    df["icon_url"] = df["item_id"].map(lambda i: meta.get(int(i), {}).get("icon_url"))

    df["tier"] = df["win_rate"].apply(tier_for)

    # Mutual-exclusion graph (upgrade variants of the same item).
    excl = compute_exclusivity(df, meta)
    df["group_key"] = df["item_id"].map(lambda i: excl.get(int(i), {}).get("group_key"))
    df["exclusive_ids"] = df["item_id"].map(lambda i: excl.get(int(i), {}).get("exclusive_ids", []))
    return df


# ---- read helpers used by routers ----

def latest_snapshot_at(db: Session) -> datetime | None:
    row = db.execute(
        select(models.ItemStat.fetched_at)
        .order_by(desc(models.ItemStat.fetched_at))
        .limit(1)
    ).first()
    return row[0] if row else None


def latest_item_stats(
    db: Session,
    category: str | None = None,
    tier: str | None = None,
    limit: int = 500,
) -> list[models.ItemStat]:
    ts = latest_snapshot_at(db)
    if ts is None:
        return []
    stmt = (
        select(models.ItemStat)
        .where(models.ItemStat.fetched_at == ts)
        .order_by(desc(models.ItemStat.confidence), desc(models.ItemStat.win_rate))
        .limit(limit)
    )
    if category:
        stmt = stmt.where(models.ItemStat.category == category.lower())
    if tier:
        stmt = stmt.where(models.ItemStat.tier == tier.upper())
    return list(db.execute(stmt).scalars().all())


# ---- pipeline-facing fetch + persist ----

async def fetch_and_persist(db: Session, fetched_at: datetime) -> int:
    """
    Pull items + analytics from upstream, normalise, insert ItemStat rows.
    Returns the number of rows inserted.
    """
    client = DeadlockClient()
    try:
        items_meta = await client.items()
    except Exception:
        items_meta = []
    mode_used = ""
    try:
        item_stats, mode_used = await client.item_stats()
    except Exception:
        item_stats = []

    df = build_item_stats(items_meta, item_stats)
    if df.empty:
        return 0

    inserted = 0
    for _, r in df.iterrows():
        excl = r.get("exclusive_ids")
        excl_json = json.dumps([int(x) for x in excl]) if isinstance(excl, (list, tuple)) and len(excl) else None
        db.add(models.ItemStat(
            item_id=int(r["item_id"]),
            fetched_at=fetched_at,
            name=str(r["name"])[:96],
            tier_slot=int(r["tier_slot"]),
            category=str(r["category"])[:24],
            matches=int(r["matches"]),
            wins=int(r["wins"]),
            win_rate=float(r["win_rate"]),
            confidence=float(r["confidence"]),
            tier=str(r["tier"]),
            icon_url=(str(r["icon_url"]) if pd.notna(r.get("icon_url")) and r.get("icon_url") else None),
            group_key=(str(r["group_key"])[:96] if r.get("group_key") else None),
            exclusive_ids=excl_json,
        ))
        inserted += 1
    return inserted
