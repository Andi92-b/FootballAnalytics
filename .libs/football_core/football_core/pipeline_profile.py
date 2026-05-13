"""
pipeline_profile.py — Orchestrates all 5 source fetchers for a player profile.

Runs fetchers concurrently where possible. Returns a ProfileResult with raw
data from each source (or an error string if a source failed).

Usage:
    registry = json.loads(Path("player_registry.json").read_text())
    result = fetch_profile("Luis Diaz", registry, Path(".cache"))
"""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class ProfileResult:
    player: str
    display_name: str
    position: str
    team: str
    # Raw data keyed by source name; None means fetch failed
    sources: dict[str, dict | None] = field(default_factory=dict)
    # Error messages for failed sources
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def available_sources(self) -> list[str]:
        return [k for k, v in self.sources.items() if v is not None]


def _run_sofascore(entry: dict, cache_dir: Path) -> dict | None:
    from football_core.sources.sofascore import fetch_sofascore
    return fetch_sofascore(
        player_id=entry["sofascore_id"],
        tournament_id=entry["sofascore_tournament_id"],
        season_id=entry["sofascore_season_id"],
        cache_dir=cache_dir,
    )


def _run_understat(entry: dict, cache_dir: Path) -> dict | None:
    from football_core.sources.understat import fetch_understat
    result = fetch_understat(
        league=entry["understat_league"],
        season=entry["understat_season"],
        cache_dir=cache_dir,
    )
    if result is None:
        return None
    # Look up this player in the league-wide dict
    import unicodedata

    def norm(s: str) -> str:
        return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower().strip()

    key = norm(entry.get("understat_name", entry.get("display_name", "")))
    return result.get(key)


def _run_fbref(entry: dict, cache_dir: Path) -> dict | None:
    from football_core.sources.fbref import fetch_fbref
    from football_core.fetcher import merge_player_stats, add_team_poss
    import unicodedata

    def norm(s: str) -> str:
        return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower().strip()

    try:
        tables = fetch_fbref(entry["fbref_league"], entry["fbref_season"], cache_dir)
        tables = add_team_poss(tables)
        display = entry.get("display_name", entry.get("name", ""))
        stats = merge_player_stats(display, tables)
        if stats is None:
            # Try ASCII fallback
            ascii_name = unicodedata.normalize("NFD", display).encode("ascii", "ignore").decode()
            stats = merge_player_stats(ascii_name, tables)
        if stats is None:
            return None
        # Coerce numpy/pandas scalar types to native Python for JSON serialisation
        try:
            import numpy as np
            return {
                k: (int(v) if isinstance(v, np.integer) else float(v) if isinstance(v, np.floating) else v)
                for k, v in stats.items()
            }
        except ImportError:
            return stats
    except Exception as exc:
        log.warning("FBref fetch failed: %s", exc)
        return None


def _run_footystats(entry: dict, cache_dir: Path) -> dict | None:
    from football_core.sources.footystats import fetch_footystats
    return fetch_footystats(slug=entry["footystats_slug"], cache_dir=cache_dir)


def _run_ovo(entry: dict, cache_dir: Path) -> dict | None:
    from football_core.sources.one_versus_one import fetch_ovo
    return fetch_ovo(slug=entry["ovo_slug"], cache_dir=cache_dir)


_FETCHERS = {
    "sofascore": _run_sofascore,
    "understat": _run_understat,
    "fbref": _run_fbref,
    "footystats": _run_footystats,
    "ovo": _run_ovo,
}


def fetch_profile(
    player_name: str,
    registry: dict,
    cache_dir: Path,
    force_refresh: bool = False,
    season: int | None = None,
    league: str | None = None,
) -> ProfileResult:
    """Fetch all 5 sources for a player concurrently and return a ProfileResult.

    If ``season`` and ``league`` are provided they override the registry defaults,
    so the dashboard data matches whatever season is displayed in the pizza chart.
    """
    # Normalise lookup
    key = next(
        (k for k in registry if k.lower() == player_name.lower()),
        None,
    )
    if key is None:
        # Fuzzy: try contains
        key = next(
            (k for k in registry if player_name.lower() in k.lower() or k.lower() in player_name.lower()),
            None,
        )
    if key is None:
        raise KeyError(f"Player '{player_name}' not found in registry. Available: {list(registry.keys())}")

    entry = dict(registry[key])  # shallow copy so we can override without mutating registry

    # Apply season/league overrides when requested
    if season is not None and league is not None:
        from football_core.sources.sofascore import (
            SOFASCORE_TOURNAMENT_IDS,
            SOFASCORE_SEASON_IDS,
        )
        entry["fbref_league"] = league
        entry["fbref_season"] = season
        entry["understat_league"] = league
        entry["understat_season"] = season
        # Resolve Sofascore tournament + season IDs for the requested league/season
        tid = SOFASCORE_TOURNAMENT_IDS.get(league)
        sid = SOFASCORE_SEASON_IDS.get((league, season))
        if tid is not None:
            entry["sofascore_tournament_id"] = tid
        if sid is not None:
            entry["sofascore_season_id"] = sid

    result = ProfileResult(
        player=key,
        display_name=entry.get("display_name", key),
        position=entry.get("position", ""),
        team=entry.get("current_team", ""),
    )

    # Run all fetchers in a thread pool (they are blocking I/O)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            source: pool.submit(fn, entry, cache_dir)
            for source, fn in _FETCHERS.items()
        }
        for source, future in futures.items():
            try:
                data = future.result(timeout=60)
                result.sources[source] = data
                if data is None:
                    result.errors[source] = "returned None (no data or not found)"
            except Exception as exc:
                result.sources[source] = None
                result.errors[source] = str(exc)
                log.warning("Source %s failed: %s", source, exc)

    log.info(
        "Profile for %s: available=%s errors=%s",
        result.display_name,
        result.available_sources,
        list(result.errors.keys()),
    )
    return result
