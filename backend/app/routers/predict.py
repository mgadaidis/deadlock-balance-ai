"""Simulator (phase-by-phase match prediction) endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..ml import predictor
from ..ml import supervised_model

router = APIRouter(prefix="/predict", tags=["simulator"])


@router.post("", response_model=schemas.SimulationResponse)
def simulate_match(req: schemas.SimulationRequest, db: Session = Depends(get_db)):
    return predictor.simulate(
        db, req.hero_ids, req.enemy_hero_ids,
        req.team_item_ids, req.enemy_item_ids,
        req.team_hero_item_builds, req.enemy_hero_item_builds,
    )


@router.get("/model-status")
def model_status(db: Session = Depends(get_db)):
    return supervised_model.model_status(db)
