"""
ORM models. Tables:
  * Hero        – static metadata
  * HeroStat    – per-hero stats snapshot (one row per refresh)
  * BalanceFlag – analyser verdict per hero
  * ItemStat    – per-item stats snapshot (one row per refresh)
"""
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Hero(Base):
    __tablename__ = "heroes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    playstyle: Mapped[str | None] = mapped_column(Text, nullable=True)

    stats: Mapped[list["HeroStat"]] = relationship(back_populates="hero", cascade="all, delete-orphan")
    flags: Mapped[list["BalanceFlag"]] = relationship(back_populates="hero", cascade="all, delete-orphan")


class HeroStat(Base):
    __tablename__ = "hero_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id"), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    matches: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)

    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    pick_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_kills: Mapped[float] = mapped_column(Float, default=0.0)
    avg_deaths: Mapped[float] = mapped_column(Float, default=0.0)
    avg_assists: Mapped[float] = mapped_column(Float, default=0.0)
    kda: Mapped[float] = mapped_column(Float, default=0.0)
    avg_damage: Mapped[float] = mapped_column(Float, default=0.0)
    avg_net_worth: Mapped[float] = mapped_column(Float, default=0.0)

    hero: Mapped["Hero"] = relationship(back_populates="stats")


class BalanceFlag(Base):
    __tablename__ = "balance_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    verdict: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    macro_impact: Mapped[str] = mapped_column(Text, default="")
    mechanical_reasoning: Mapped[str] = mapped_column(Text, default="")

    hero: Mapped["Hero"] = relationship(back_populates="flags")


class ItemStat(Base):
    __tablename__ = "item_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(Integer, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    name: Mapped[str] = mapped_column(String(96), default="")
    tier_slot: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str] = mapped_column(String(24), default="")
    matches: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    tier: Mapped[str] = mapped_column(String(2), default="C")
    icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Upgrade-family label and the ids this item is mutually exclusive with
    # (a JSON list of ints, stored as text). Populated by items_service from
    # upstream component data plus the bundled item-relations fallback.
    group_key: Mapped[str | None] = mapped_column(String(96), nullable=True)
    exclusive_ids: Mapped[str | None] = mapped_column(Text, nullable=True)


class AbilityPathStat(Base):
    """Optional ability-upgrade-path analytics from Deadlock API.

    These rows are only populated when the upstream ability endpoint is available.
    They store upgrade-path win rates, not per-cast damage or direct OP-proof.
    """
    __tablename__ = "ability_path_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id"), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    path_label: Mapped[str] = mapped_column(Text, default="")
    matches: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    pick_rate: Mapped[float] = mapped_column(Float, default=0.0)
    item_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_note: Mapped[str] = mapped_column(Text, default="Deadlock API ability upgrade-path analytics")

    hero: Mapped["Hero"] = relationship()
