"""Pydantic wire schemas."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class HeroBase(BaseModel):
    id: int
    name: str
    role: str | None = None
    image_url: str | None = None
    model_config = ConfigDict(from_attributes=True)


class HeroStatOut(BaseModel):
    hero_id: int
    name: str
    image_url: str | None = None
    matches: int
    wins: int
    losses: int
    win_rate: float
    pick_rate: float
    avg_kills: float
    avg_deaths: float
    avg_assists: float
    kda: float
    avg_damage: float
    avg_net_worth: float
    fetched_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BalanceFlagOut(BaseModel):
    hero_id: int
    name: str
    image_url: str | None = None
    verdict: str
    score: float
    rationale: str
    recommendation: str
    macro_impact: str
    mechanical_reasoning: str
    win_rate: float
    pick_rate: float
    kda: float
    avg_damage: float
    created_at: datetime

    # Supervised ML recommendation evidence. These are optional so the
    # recommendations endpoint still works before enough rows exist to train.
    ml_predicted_win_rate: float | None = None
    ml_observed_gap: float | None = None
    ml_interpretation: str | None = None
    ml_balance_class: str | None = None
    ml_balance_confidence: float | None = None
    ml_class_probabilities: dict[str, float] | None = None
    model_config = ConfigDict(from_attributes=True)


# ---- items ----

class ItemStatOut(BaseModel):
    item_id: int
    name: str
    icon_url: str | None = None
    category: str
    tier_slot: int
    matches: int
    win_rate: float
    confidence: float
    tier: str
    group_key: str | None = None
    exclusive_ids: list[int] = []
    model_config = ConfigDict(from_attributes=True)


class ItemRecommendationOut(BaseModel):
    item_id: int
    name: str
    icon_url: str | None = None
    category: str
    tier: str
    matches: int
    win_rate: float
    confidence: float
    usage_rate: float
    verdict: str
    severity: str
    evidence: str
    recommendation: str
    simulation_note: str
    exclusive_ids: list[int] = []
    exclusive_names: list[str] = []
    model_config = ConfigDict(from_attributes=True)


class AbilityPathOut(BaseModel):
    hero_id: int
    hero_name: str | None = None
    path_label: str
    matches: int
    wins: int
    win_rate: float
    pick_rate: float
    item_context: str | None = None
    source_note: str
    model_config = ConfigDict(from_attributes=True)


# ---- simulator ----

class SimulationRequest(BaseModel):
    hero_ids: list[int]
    enemy_hero_ids: list[int] | None = None
    # Backward-compatible global build fields. New UI sends per-hero builds below.
    team_item_ids: list[int] | None = None
    enemy_item_ids: list[int] | None = None
    team_hero_item_builds: dict[str, list[int]] | None = None
    enemy_hero_item_builds: dict[str, list[int]] | None = None


class SimulationPhase(BaseModel):
    phase: str                  # "early" | "mid" | "late"
    time_range: str             # human label, e.g. "0–10 min"
    team_advantage: float       # -1..+1
    events: list[str]
    headline: str


class SimulationResponse(BaseModel):
    win_probability: float
    team_avg_win_rate: float
    enemy_avg_win_rate: float | None
    team_build_compatibility: float | None = None
    enemy_build_compatibility: float | None = None
    phases: list[SimulationPhase]
    summary: str
    item_analysis: list[str] = []
    model_note: str | None = None


# ---- meta-shift ----

class MetaShiftEntry(BaseModel):
    hero_id: int
    name: str
    win_rate: float
    win_rate_delta: float       # current - previous
    pick_rate: float
    pick_rate_delta: float
    direction: str              # "rising" | "falling" | "stable"


class MetaShiftResponse(BaseModel):
    current_snapshot: datetime | None
    previous_snapshot: datetime | None
    entries: list[MetaShiftEntry]


# ---- pipeline ----

class RefreshResponse(BaseModel):
    heroes_loaded: int
    stats_inserted: int
    items_inserted: int
    flags_generated: int
    fetched_at: datetime
    match_mode: str = ""
    mode_param_used: str = ""
    upstream_heroes: int = 0
    upstream_stats: int = 0
    errors: list[str] = []
    ability_paths_inserted: int = 0
