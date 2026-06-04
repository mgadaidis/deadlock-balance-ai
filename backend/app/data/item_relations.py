"""
Item upgrade/exclusivity relationships loaded from data files.

This module does not hard-code the item upgrade graph in Python.  It reads
``item_upgrade_paths.json`` so new item paths can be added for the simulator / ML
pipeline without changing code.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

UPGRADE_QUALIFIERS = {
    "basic", "improved", "mystic", "greater", "superior", "refined",
    "enchanted", "heroic", "empowered", "advanced", "extended", "high",
}

_ROMAN = {"i", "ii", "iii", "iv", "v", "vi"}
_PUNCT = re.compile(r"[^a-z0-9 ]+")


def _norm(name: str) -> str:
    return _PUNCT.sub(" ", (name or "").lower()).strip()


def family_stem(name: str) -> str:
    s = _norm(name)
    tokens = [t for t in s.split() if t and t not in _ROMAN]
    while tokens and tokens[0] in UPGRADE_QUALIFIERS:
        tokens.pop(0)
    return " ".join(tokens)


@lru_cache(maxsize=1)
def upgrade_seed() -> dict:
    path = Path(__file__).with_name("item_upgrade_paths.json")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"paths": []}


@lru_cache(maxsize=1)
def curated_groups() -> dict[str, set[str]]:
    """Return upgrade families as {family_label: {lower-case item names}}."""
    out: dict[str, set[str]] = {}
    for row in upgrade_seed().get("paths", []):
        base = row.get("base")
        names = [base, *(row.get("upgrades") or [])]
        names = [_norm(n) for n in names if n]
        if len(names) < 2:
            continue
        label = f"{row.get('category','unknown')}:{names[0]}"
        out[label] = set(names)
    return out


def sources() -> list[dict]:
    return list(upgrade_seed().get("sources", []))



@lru_cache(maxsize=1)
def curated_edges() -> list[dict]:
    """Return direct upgrade edges from item_upgrade_paths.json.

    This is intentionally not a full-family clique. If one base item branches
    into two upgrades, the two upgrades are both connected to the base but not
    to each other. Example: Rapid Rounds <-> Swift Striker and Rapid Rounds <->
    Burst Fire; Swift Striker and Burst Fire remain selectable together.
    """
    out: list[dict] = []
    for row in upgrade_seed().get("paths", []):
        base = row.get("base")
        if not base:
            continue
        for up in row.get("upgrades") or []:
            if not up:
                continue
            out.append({
                "category": row.get("category", "unknown"),
                "base": _norm(base),
                "upgrade": _norm(up),
                "label": f"{row.get('category','unknown')}:{_norm(base)}",
            })
    return out
