"""Items endpoints — backed entirely by the items_service module."""
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import items_service, schemas
from ..database import get_db

router = APIRouter(prefix="/items", tags=["items"])


def _parse_exclusive(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return [int(x) for x in val] if isinstance(val, list) else []
    except (ValueError, TypeError):
        return []


def _to_out(r) -> schemas.ItemStatOut:
    return schemas.ItemStatOut(
        item_id=r.item_id, name=r.name, icon_url=r.icon_url,
        category=r.category, tier_slot=r.tier_slot,
        matches=r.matches, win_rate=r.win_rate,
        confidence=r.confidence, tier=r.tier,
        group_key=r.group_key,
        exclusive_ids=_parse_exclusive(r.exclusive_ids),
    )


@router.get("", response_model=list[schemas.ItemStatOut])
def list_items(
    category: str | None = None,
    tier: str | None = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    rows = items_service.latest_item_stats(db, category=category, tier=tier, limit=limit)
    return [_to_out(r) for r in rows]


@router.get("/tier-list", response_model=dict[str, list[schemas.ItemStatOut]])
def tier_list(db: Session = Depends(get_db)):
    """Items grouped by tier letter — what the Overview page renders."""
    rows = items_service.latest_item_stats(db, limit=2000)
    buckets: dict[str, list[schemas.ItemStatOut]] = {t: [] for t in "SABCD"}
    for r in rows:
        buckets.setdefault(r.tier, []).append(_to_out(r))
    # Within each tier, sort by win rate
    for t in buckets:
        buckets[t].sort(key=lambda x: x.win_rate, reverse=True)
    return buckets



def _item_verdict(r, usage_rate: float) -> tuple[str, str]:
    """Return (verdict, severity) from win rate + usage.

    Usage matters because a high win rate on a rarely purchased item is a niche
    signal, not the same thing as broad overperformance.
    """
    wr = float(r.win_rate or 0.0)
    conf = float(r.confidence or 0.0)

    high_wr = wr >= 0.530
    very_high_wr = wr >= 0.555
    low_wr = wr <= 0.470
    very_low_wr = wr <= 0.455

    # Relative usage bands.  These are intentionally conservative because item
    # analytics are aggregate rows, not per-hero build rows.
    low_usage = usage_rate < 0.006
    high_usage = usage_rate >= 0.020

    if very_high_wr and high_usage and conf >= 0.65:
        return "broad overperformance", "high"
    if high_wr and low_usage:
        return "niche strong / investigate", "medium"
    if high_wr:
        return "strong / watchlist", "medium"

    if very_low_wr and high_usage and conf >= 0.65:
        return "popular but weak", "high"
    if low_wr and low_usage:
        return "niche weak / low priority", "low"
    if low_wr:
        return "weak / watchlist", "medium"

    if high_usage and wr < 0.500:
        return "popular inefficient", "medium"
    return "stable", "low"


def _usage_label(usage_rate: float) -> str:
    if usage_rate >= 0.020:
        return "high usage"
    if usage_rate < 0.006:
        return "low usage"
    return "moderate usage"


def _item_recommendation_text(r, verdict: str, exclusive_names: list[str], usage_rate: float) -> tuple[str, str, str]:
    category = (r.category or "unknown").lower()
    wr_pct = float(r.win_rate or 0.0) * 100
    usage_pct = usage_rate * 100
    confidence = float(r.confidence or 0.0)
    usage_label = _usage_label(usage_rate)

    evidence = (
        f"{r.name} is a {category} item with {wr_pct:.1f}% observed win rate and "
        f"{usage_pct:.2f}% relative usage share across {int(r.matches):,} item-stat matches. "
        f"The confidence score is {confidence:.2f}. This means the result is read as {usage_label}: "
    )
    if usage_label == "low usage":
        evidence += "a high win rate may come from niche heroes, specialist players, late-game purchases, or already-winning builds rather than the item being globally broken."
    elif usage_label == "high usage":
        evidence += "many builds are buying it, so its win-rate signal is more important for global balance."
    else:
        evidence += "the item has enough usage to monitor, but hero-specific build data is still needed before making large changes."

    if exclusive_names:
        evidence += " Direct upgrade/exclusion relation: cannot be selected together with " + ", ".join(exclusive_names[:6]) + "."

    if verdict == "broad overperformance":
        rec = (
            "High-priority item review. The item has both high win rate and high usage, so it is more likely to be broadly efficient rather than only niche. "
            "Review cost, timing, stat budget, and whether too many heroes can use it successfully."
        )
    elif verdict == "niche strong / investigate":
        rec = (
            "Do not apply an immediate global nerf. The win rate is high but usage is low, so first inspect which heroes/builds buy it and whether it is only strong in specialist scenarios."
        )
    elif verdict == "strong / watchlist":
        rec = (
            "Keep on watchlist. The item is above neutral, but the action should depend on hero-item build data: broad usage points to item tuning, narrow usage points to synergy tuning."
        )
    elif verdict == "popular but weak":
        rec = (
            "Investigate as a possible trap item. It is bought often but loses too much, which may mean players overvalue it, buy it at the wrong timing, or its stats are inefficient."
        )
    elif verdict == "popular inefficient":
        rec = (
            "Watch as a high-usage inefficient item. Consider tooltip/build-path clarity or a small efficiency adjustment if future snapshots show the same pattern."
        )
    elif verdict == "niche weak / low priority":
        rec = (
            "Low-priority change. The item is weak and rarely bought, so it may be niche or misunderstood; buff only after checking whether any hero actually depends on it."
        )
    elif verdict == "weak / watchlist":
        rec = (
            "Monitor as a weak item. Do not buff blindly; first check whether low performance comes from niche use, late purchase timing, or poor hero compatibility."
        )
    else:
        rec = (
            "No immediate balance action. The item sits close to the healthy range and should mainly be monitored for future patch or meta changes."
        )

    sim = (
        "Simulator impact: this item contributes through global item performance, relative usage, category fit, confidence, and direct upgrade restrictions. "
        "High win rate with low usage is treated as niche evidence, while high win rate with high usage is treated as a broader balance signal."
    )
    return evidence, rec, sim



@router.get("/recommendations", response_model=dict[str, list[schemas.ItemRecommendationOut]])
def item_recommendations(db: Session = Depends(get_db)):
    """Categorized item balance recommendations.

    This endpoint is intentionally separate from hero recommendations because
    there are many items. The frontend renders categories first, then expands
    a single item to show its full case file.
    """
    rows = items_service.latest_item_stats(db, limit=2000)
    by_id = {r.item_id: r for r in rows}
    total_item_matches = sum(max(int(r.matches or 0), 0) for r in rows) or 1
    buckets: dict[str, list[schemas.ItemRecommendationOut]] = {
        "weapon": [], "spirit": [], "vitality": []
    }

    for r in rows:
        exclusive_ids = _parse_exclusive(r.exclusive_ids)
        exclusive_names = [by_id[i].name for i in exclusive_ids if i in by_id]
        usage_rate = max(int(r.matches or 0), 0) / total_item_matches
        verdict, severity = _item_verdict(r, usage_rate)
        evidence, rec, sim = _item_recommendation_text(r, verdict, exclusive_names, usage_rate)
        raw_cat = (r.category or "").lower()
        if "weapon" in raw_cat:
            cat = "weapon"
        elif "spirit" in raw_cat:
            cat = "spirit"
        elif "vital" in raw_cat or "health" in raw_cat:
            cat = "vitality"
        else:
            # Only show the three real shop categories in the item recommendation UI.
            # Items with unknown/other category remain available through /items and
            # Overview tier lists, but they are excluded from this focused page.
            continue
        buckets.setdefault(cat, []).append(schemas.ItemRecommendationOut(
            item_id=r.item_id,
            name=r.name,
            icon_url=r.icon_url,
            category=cat,
            tier=r.tier,
            matches=r.matches,
            win_rate=r.win_rate,
            confidence=r.confidence,
            usage_rate=usage_rate,
            verdict=verdict,
            severity=severity,
            evidence=evidence,
            recommendation=rec,
            simulation_note=sim,
            exclusive_ids=exclusive_ids,
            exclusive_names=exclusive_names,
        ))

    for cat in buckets:
        buckets[cat].sort(key=lambda x: ({"high": 3, "medium": 2, "low": 1}.get(x.severity, 0), abs(x.win_rate - 0.5), x.confidence), reverse=True)
    return buckets
