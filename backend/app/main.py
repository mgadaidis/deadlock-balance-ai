"""FastAPI entry point."""
from contextlib import asynccontextmanager
from datetime import datetime
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, desc, select
from . import models
from .config import settings
from .data_pipeline import refresh_all
from .database import SessionLocal, init_db
from .deadlock_client import DeadlockClient
from .routers import balance, heroes, items, predict
from .schemas import RefreshResponse
from .ml import supervised_model

refresh_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Deadlock Balance AI",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(heroes.router)
app.include_router(balance.router)
app.include_router(items.router)
app.include_router(predict.router)


@app.get("/")
def root():
    return {
        "name": "Deadlock Balance AI",
        "docs": "/docs",
        "diagnose": "/diagnose",
        "configured_mode": settings.match_mode,
    }


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/data-status")
def data_status():
    """Local DB status only. Use this to tell whether the app has data cached
    without waiting for public APIs or triggering refresh."""
    db = SessionLocal()
    try:
        latest_stat = db.execute(
            select(models.HeroStat.fetched_at).order_by(desc(models.HeroStat.fetched_at)).limit(1)
        ).scalar()
        latest_flag = db.execute(
            select(models.BalanceFlag.created_at).order_by(desc(models.BalanceFlag.created_at)).limit(1)
        ).scalar()
        return {
            "backend": "ok",
            "latest_hero_snapshot": str(latest_stat) if latest_stat else None,
            "latest_recommendation_snapshot": str(latest_flag) if latest_flag else None,
            "heroes": db.execute(select(func.count(models.Hero.id))).scalar() or 0,
            "hero_stats": db.execute(select(func.count(models.HeroStat.id))).scalar() or 0,
            "balance_flags": db.execute(select(func.count(models.BalanceFlag.id))).scalar() or 0,
            "items": db.execute(select(func.count(models.ItemStat.id))).scalar() or 0,
            "ability_paths": db.execute(select(func.count(models.AbilityPathStat.id))).scalar() or 0,
        }
    finally:
        db.close()


@app.get("/diagnose")
async def diagnose():
    """
    Does NOT touch the DB. Calls each upstream endpoint and reports how many
    rows came back, which mode-filter param (if any) succeeded, and full
    exception text on failure. Use this when refresh appears to do nothing.
    """
    client = DeadlockClient()
    out: dict = {
        "configured_mode": settings.match_mode,
        "deadlock_api_base": settings.deadlock_api_base,
        "deadlock_assets_base": settings.deadlock_assets_base,
    }

    try:
        heroes = await client.heroes()
        out["heroes"] = {"count": len(heroes), "sample_keys": list(heroes[0].keys()) if heroes else []}
    except Exception as e:
        out["heroes"] = {"error": str(e)}

    try:
        stats, mode_used = await client.hero_stats()
        out["hero_stats"] = {
            "count": len(stats),
            "mode_param_used": mode_used or "(unfiltered)",
            "sample_keys": list(stats[0].keys()) if stats else [],
        }
    except Exception as e:
        out["hero_stats"] = {"error": str(e)}

    try:
        items, mode_used = await client.item_stats()
        out["item_stats"] = {
            "count": len(items),
            "mode_param_used": mode_used or "(unfiltered)",
            "sample_keys": list(items[0].keys()) if items else [],
        }
    except Exception as e:
        out["item_stats"] = {"error": str(e)}

    try:
        items_meta = await client.items()
        out["items_meta"] = {"count": len(items_meta)}
    except Exception as e:
        out["items_meta"] = {"error": str(e)}

    try:
        ability_rows, ability_path = await client.ability_stats()
        out["ability_stats"] = {
            "count": len(ability_rows),
            "endpoint_used": ability_path or "(none)",
            "sample_keys": list(ability_rows[0].keys()) if ability_rows else [],
        }
    except Exception as e:
        out["ability_stats"] = {"error": str(e)}

    return out


@app.post("/refresh", response_model=RefreshResponse)
async def refresh():
    # Only one refresh may write to SQLite at a time. This prevents accidental
    # double-clicks, frontend retries, or two open browser tabs from colliding
    # and producing "sqlite3.OperationalError: database is locked".
    if refresh_lock.locked():
        raise HTTPException(status_code=409, detail="Refresh is already running. Wait for it to finish, then try again.")
    async with refresh_lock:
        db = SessionLocal()
        try:
            result = await refresh_all(db)
            # Refresh creates a new snapshot. Clear the ML cache so the next
            # simulator/recommendations request trains once on the new rows,
            # then reuses that trained model for fast page loads.
            supervised_model.clear_model_cache()
            # Warm the supervised model once during refresh. This makes the
            # Recommendations and Simulator pages appear quickly afterward
            # instead of each page training the model on first visit.
            try:
                supervised_model.train_hero_winrate_model(db)
            except Exception:
                # ML evidence is an enhancement; refresh data should still be
                # available even if the model cannot train on a small snapshot.
                pass
            return result
        finally:
            db.close()
