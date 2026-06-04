"""Endpoints exposing hero metadata and latest stats."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .. import ability_service, models, schemas
from ..database import get_db

router = APIRouter(prefix="/heroes", tags=["heroes"])


@router.get("", response_model=list[schemas.HeroBase])
def list_heroes(db: Session = Depends(get_db)):
    # Only expose heroes with observed stats in the latest snapshot. This keeps
    # unreleased/test placeholders (Gunslinger, Swan, etc.) out of the app.
    latest = db.execute(
        select(models.HeroStat.fetched_at)
        .order_by(desc(models.HeroStat.fetched_at))
        .limit(1)
    ).first()
    if latest is None:
        return db.execute(select(models.Hero).order_by(models.Hero.name)).scalars().all()
    fetched_at: datetime = latest[0]
    rows = db.execute(
        select(models.Hero)
        .join(models.HeroStat, models.Hero.id == models.HeroStat.hero_id)
        .where(models.HeroStat.fetched_at == fetched_at)
        .where(models.HeroStat.matches > 0)
        .order_by(models.Hero.name)
    ).scalars().all()
    return rows


@router.get("/stats", response_model=list[schemas.HeroStatOut])
def latest_stats(db: Session = Depends(get_db)):
    """
    Latest snapshot per hero. We pick the most recent fetched_at and return
    all rows from that timestamp, joined with hero names for convenience.
    """
    latest = db.execute(
        select(models.HeroStat.fetched_at)
        .order_by(desc(models.HeroStat.fetched_at))
        .limit(1)
    ).first()
    if latest is None:
        raise HTTPException(404, "No stats yet — call POST /refresh first.")
    fetched_at: datetime = latest[0]

    rows = db.execute(
        select(models.HeroStat, models.Hero.name, models.Hero.image_url)
        .join(models.Hero, models.Hero.id == models.HeroStat.hero_id)
        .where(models.HeroStat.fetched_at == fetched_at)
        .order_by(desc(models.HeroStat.win_rate))
    ).all()

    return [
        schemas.HeroStatOut(
            hero_id=stat.hero_id,
            name=name,
            image_url=image_url,
            matches=stat.matches,
            wins=stat.wins,
            losses=stat.losses,
            win_rate=stat.win_rate,
            pick_rate=stat.pick_rate,
            avg_kills=stat.avg_kills,
            avg_deaths=stat.avg_deaths,
            avg_assists=stat.avg_assists,
            kda=stat.kda,
            avg_damage=stat.avg_damage,
            avg_net_worth=stat.avg_net_worth,
            fetched_at=stat.fetched_at,
        )
        for stat, name, image_url in rows
    ]


@router.get("/{hero_id}/stats", response_model=list[schemas.HeroStatOut])
def hero_history(hero_id: int, db: Session = Depends(get_db)):
    """Time series of a single hero's stats — useful for trend charts."""
    hero = db.get(models.Hero, hero_id)
    if hero is None:
        raise HTTPException(404, "Hero not found")

    rows = db.execute(
        select(models.HeroStat)
        .where(models.HeroStat.hero_id == hero_id)
        .order_by(models.HeroStat.fetched_at)
    ).scalars().all()

    return [
        schemas.HeroStatOut(
            hero_id=s.hero_id,
            name=hero.name,
            image_url=hero.image_url,
            matches=s.matches,
            wins=s.wins,
            losses=s.losses,
            win_rate=s.win_rate,
            pick_rate=s.pick_rate,
            avg_kills=s.avg_kills,
            avg_deaths=s.avg_deaths,
            avg_assists=s.avg_assists,
            kda=s.kda,
            avg_damage=s.avg_damage,
            avg_net_worth=s.avg_net_worth,
            fetched_at=s.fetched_at,
        )
        for s in rows
    ]


@router.get("/{hero_id}/abilities", response_model=list[schemas.AbilityPathOut])
def ability_paths(hero_id: int, db: Session = Depends(get_db)):
    hero = db.get(models.Hero, hero_id)
    if hero is None:
        raise HTTPException(404, "Hero not found")
    rows = ability_service.latest_for_hero(db, hero_id, limit=12)
    return [
        schemas.AbilityPathOut(
            hero_id=r.hero_id, hero_name=hero.name, path_label=r.path_label,
            matches=r.matches, wins=r.wins, win_rate=r.win_rate, pick_rate=r.pick_rate,
            item_context=r.item_context, source_note=r.source_note,
        ) for r in rows
    ]
