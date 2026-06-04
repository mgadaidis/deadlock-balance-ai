"""
Async client for the Deadlock API.

The upstream's mode-filter parameter name varies by endpoint and release.
We try a small list of plausible parameter names; the first one that comes
back non-empty wins. If a mode is configured but none of the attempts work,
we fall back to the unfiltered call and report it via the returned tuple
so the caller can surface the situation in the UI.
"""
from __future__ import annotations

from typing import Any
import httpx

from .config import settings


# Candidate parameter names, in priority order. `game_mode` first because
# "Normal" / "StreetBrawl" are *game-mode* values on the Deadlock API site.
_MODE_PARAM_CANDIDATES = ("game_mode", "match_mode", "match_modes")


class DeadlockClient:
    def __init__(self, timeout: float = 45.0) -> None:
        self._api = settings.deadlock_api_base.rstrip("/")
        self._assets = settings.deadlock_assets_base.rstrip("/")
        self._timeout = timeout
        self._mode = (settings.match_mode or "").strip()

    async def _get(self, base: str, path: str, params: dict | None = None) -> Any:
        url = f"{base}{path}"
        # Deadlock's public assets endpoints sometimes issue permanent redirects
        # from assets.deadlock-api.com to api.deadlock-api.com.  Without
        # follow_redirects=True, httpx raises on the 301 and the app silently
        # ends up with empty metadata/icons.
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()

    async def _get_with_mode_fallback(self, path: str) -> tuple[list[dict], str]:
        """
        Call `path` once per mode-param candidate until one returns a non-empty
        list, then fall back to the unfiltered call. Returns `(data, used_param)`
        where `used_param` is the parameter name we actually used (empty string
        for unfiltered).
        """
        if self._mode:
            for param_name in _MODE_PARAM_CANDIDATES:
                try:
                    data = await self._get(self._api, path, params={param_name: self._mode})
                    if isinstance(data, list) and len(data) > 0:
                        return data, param_name
                except httpx.HTTPError:
                    continue
        # No mode set, or every candidate returned empty / errored:
        # fall back to the unfiltered endpoint so the page never goes blank.
        data = await self._get(self._api, path)
        return (data if isinstance(data, list) else []), ""

    # ---- assets ----

    async def heroes(self) -> list[dict]:
        # Prefer the canonical API endpoint, then fall back to legacy assets.
        for base, path in (
            (self._api, "/v1/assets/heroes"),
            (self._assets, "/v2/heroes"),
        ):
            try:
                data = await self._get(base, path)
                if isinstance(data, list):
                    return data
            except httpx.HTTPError:
                continue
        return []

    async def items(self) -> list[dict]:
        # Prefer canonical API endpoint, but keep older assets endpoints for
        # compatibility. Item icons are taken only from upstream metadata.
        for base, path in (
            (self._api, "/v1/assets/items"),
            (self._assets, "/v2/items"),
            (self._assets, "/v1/items"),
        ):
            try:
                data = await self._get(base, path)
                if isinstance(data, list):
                    return data
            except httpx.HTTPError:
                continue
        return []

    # ---- analytics ----

    async def hero_stats(self) -> tuple[list[dict], str]:
        return await self._get_with_mode_fallback("/v1/analytics/hero-stats")

    async def item_stats(self) -> tuple[list[dict], str]:
        try:
            return await self._get_with_mode_fallback("/v1/analytics/item-stats")
        except httpx.HTTPError:
            return [], ""

    async def ability_stats(self, hero_id: int | None = None, item_ids: list[int] | None = None) -> tuple[list[dict], str]:
        """Optional ability upgrade-path analytics.

        The public website exposes ability upgrade-path win rates, but the exact
        API route can change.  We try a few documented/observed naming patterns
        and fail closed.  The app never fabricates ability data; empty result
        means the UI/recommender will fall back to aggregate hero/item stats.
        """
        paths = (
            "/v1/analytics/ability-stats",
            "/v1/analytics/ability-path-stats",
            "/v1/analytics/ability-order-stats",
            "/v1/analytics/ability-upgrade-stats",
            "/v1/analytics/ability-builds",
        )
        base_params: dict[str, object] = {"min_matches": 20}
        if hero_id is not None:
            base_params["hero_id"] = hero_id
        if item_ids:
            # Different upstream clients use comma strings for list filters; if
            # unsupported, the request simply fails and we fall back.
            base_params["item_ids"] = ",".join(str(i) for i in item_ids)

        for path in paths:
            try:
                params = dict(base_params)
                if self._mode:
                    params["match_mode"] = self._mode
                data = await self._get(self._api, path, params=params or None)
                if isinstance(data, list):
                    return data, path
                if isinstance(data, dict):
                    for key in ("data", "results", "paths", "ability_paths", "items"):
                        value = data.get(key)
                        if isinstance(value, list):
                            return value, path
            except httpx.HTTPError:
                continue
        return [], ""
