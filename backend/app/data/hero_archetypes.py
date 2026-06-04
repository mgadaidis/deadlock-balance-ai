"""
Hero archetype affinities (compatibility fallback).

The simulator scores how well an item *category* (weapon / spirit / vitality)
fits a hero. With no hero-item pair statistics in the public API, the base
model infers that fit purely from a hero's aggregate stats, which is noisy for
heroes whose numbers sit close to the roster median.

Per the project rule — *gather the data elsewhere when the current API does not
provide it* — this module supplies a compact, name-keyed table of category
leanings drawn from each hero's well-understood kit. Values are multipliers
centred on 1.0:

    > 1.0  → the category suits the hero (items in it should help more)
    < 1.0  → the category fights the hero's identity (items help less)

These are *nudges*. ``predictor._hero_affinity`` blends them with the live
numeric profile, so real stats still lead and a hero missing from this table
simply falls back to the pure numeric heuristic. Lookups are case-insensitive
and any unknown hero is ignored, so the table is always safe to extend.
"""
from __future__ import annotations

# name (lower-case) -> {"weapon": m, "spirit": m, "vitality": m}
HERO_ARCHETYPES: dict[str, dict[str, float]] = {
    "abrams":      {"weapon": 1.05, "spirit": 0.95, "vitality": 1.20},
    "bebop":       {"weapon": 1.10, "spirit": 1.10, "vitality": 1.05},
    "dynamo":      {"weapon": 0.95, "spirit": 1.20, "vitality": 1.10},
    "grey talon":  {"weapon": 1.20, "spirit": 1.10, "vitality": 0.90},
    "haze":        {"weapon": 1.30, "spirit": 0.85, "vitality": 0.95},
    "infernus":    {"weapon": 1.15, "spirit": 1.15, "vitality": 0.95},
    "ivy":         {"weapon": 1.00, "spirit": 1.20, "vitality": 1.05},
    "kelvin":      {"weapon": 0.95, "spirit": 1.20, "vitality": 1.10},
    "lady geist":  {"weapon": 0.95, "spirit": 1.25, "vitality": 1.00},
    "lash":        {"weapon": 1.10, "spirit": 1.10, "vitality": 1.05},
    "mcginnis":    {"weapon": 1.15, "spirit": 1.10, "vitality": 1.00},
    "mirage":      {"weapon": 1.10, "spirit": 1.15, "vitality": 0.95},
    "mo & krill":  {"weapon": 1.05, "spirit": 1.00, "vitality": 1.20},
    "paradox":     {"weapon": 1.10, "spirit": 1.15, "vitality": 0.95},
    "pocket":      {"weapon": 1.00, "spirit": 1.25, "vitality": 0.95},
    "seven":       {"weapon": 1.15, "spirit": 1.20, "vitality": 0.90},
    "shiv":        {"weapon": 1.25, "spirit": 0.90, "vitality": 1.00},
    "vindicta":    {"weapon": 1.30, "spirit": 0.90, "vitality": 0.85},
    "viscous":     {"weapon": 1.05, "spirit": 1.15, "vitality": 1.10},
    "warden":      {"weapon": 1.10, "spirit": 1.00, "vitality": 1.15},
    "wraith":      {"weapon": 1.20, "spirit": 1.10, "vitality": 0.90},
    "yamato":      {"weapon": 1.15, "spirit": 1.00, "vitality": 1.10},
    "holliday":    {"weapon": 1.15, "spirit": 1.00, "vitality": 1.05},
    "calico":      {"weapon": 1.20, "spirit": 1.00, "vitality": 0.95},
    "sinclair":    {"weapon": 0.90, "spirit": 1.30, "vitality": 0.95},
    "vyper":       {"weapon": 1.25, "spirit": 0.95, "vitality": 0.95},
    "mina":        {"weapon": 0.95, "spirit": 1.25, "vitality": 1.00},
    "drifter":     {"weapon": 1.15, "spirit": 1.10, "vitality": 1.00},
    "paige":       {"weapon": 0.95, "spirit": 1.25, "vitality": 1.00},
    "billy":       {"weapon": 1.20, "spirit": 1.00, "vitality": 1.00},
    "doorman":     {"weapon": 1.05, "spirit": 1.15, "vitality": 1.05},
    "victor":      {"weapon": 1.10, "spirit": 1.10, "vitality": 1.00},
}


def affinity_for(name: str) -> dict[str, float] | None:
    """Return the archetype multipliers for a hero name, or None if unknown."""
    if not name:
        return None
    return HERO_ARCHETYPES.get(name.strip().lower())
