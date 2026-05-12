"""
routers/profile.py — GET /api/player/{name}/profile

Returns all available source data for a player, merged into a
structured response with per-category stat groups and source attribution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from football_core.pipeline_profile import fetch_profile, ProfileResult

router = APIRouter(prefix="/api/player", tags=["profile"])

_REGISTRY_PATH = Path(__file__).parents[3] / "player_registry.json"
_CACHE_DIR = Path(__file__).parents[3] / ".cache"


def _load_registry() -> dict:
    return json.loads(_REGISTRY_PATH.read_text())


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class StatEntry(BaseModel):
    value: float
    source: str  # "sofascore" | "fbref" | "understat" | "footystats" | "ovo"


class StatGroup(BaseModel):
    category: str
    stats: dict[str, StatEntry]


class ProfileResponse(BaseModel):
    player: str
    display_name: str
    position: str
    team: str
    available_sources: list[str]
    errors: dict[str, str]
    # Flat merged stats with source attribution
    merged: dict[str, StatEntry]
    # Raw per-source data for debug / frontend use
    raw: dict[str, Any]


# ---------------------------------------------------------------------------
# Stat merging
# ---------------------------------------------------------------------------

def _merge_stats(result: ProfileResult) -> dict[str, StatEntry]:
    """Build a merged stats dict from all sources, with source attribution.

    Priority order for conflicts: sofascore > understat > footystats > ovo > fbref
    """
    merged: dict[str, StatEntry] = {}

    def _set(key: str, value: float | int | None, source: str) -> None:
        if value is None:
            return
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        if key not in merged:
            merged[key] = StatEntry(value=round(v, 3), source=source)

    # --- Sofascore (highest priority for these stats) ---
    ss = result.sources.get("sofascore") or {}
    _set("rating", ss.get("rating"), "sofascore")
    _set("goals", ss.get("goals"), "sofascore")
    _set("assists", ss.get("assists"), "sofascore")
    _set("xa", ss.get("expectedAssists"), "sofascore")
    _set("key_passes", ss.get("keyPasses"), "sofascore")
    _set("total_passes", ss.get("totalPasses"), "sofascore")
    _set("pass_accuracy_pct", ss.get("accuratePassesPercentage"), "sofascore")
    _set("passes_own_half", ss.get("accurateOwnHalfPasses"), "sofascore")
    _set("passes_opp_half", ss.get("accurateOppositionHalfPasses"), "sofascore")
    _set("passes_final_third", ss.get("accurateFinalThirdPasses"), "sofascore")
    _set("successful_dribbles", ss.get("successfulDribbles"), "sofascore")
    _set("dribble_success_pct", ss.get("successfulDribblesPercentage"), "sofascore")
    _set("tackles", ss.get("tackles"), "sofascore")
    _set("interceptions", ss.get("interceptions"), "sofascore")
    _set("yellow_cards", ss.get("yellowCards"), "sofascore")
    _set("red_cards", ss.get("redCards"), "sofascore")
    _set("accurate_crosses", ss.get("accurateCrosses"), "sofascore")
    _set("cross_accuracy_pct", ss.get("accurateCrossesPercentage"), "sofascore")
    _set("total_shots", ss.get("totalShots"), "sofascore")
    _set("shots_on_target", ss.get("shotsOnTarget"), "sofascore")
    _set("big_chances_created", ss.get("bigChancesCreated"), "sofascore")
    _set("big_chances_missed", ss.get("bigChancesMissed"), "sofascore")
    _set("goals_assists_sum", ss.get("goalsAssistsSum"), "sofascore")

    # --- Understat (npxG / xG best from this source) ---
    us = result.sources.get("understat") or {}
    _set("npxg", us.get("npxG"), "understat")
    _set("xg", us.get("xG"), "understat")
    _set("shots_understat", us.get("shots"), "understat")

    # --- FBref (minutes is most reliable here) ---
    fb = result.sources.get("fbref") or {}
    for min_key in ("standard.Playing Time_Min", "standard.Min"):
        if fb.get(min_key) is not None:
            _set("minutes", fb[min_key], "fbref")
            break
    _set("goals_fbref", fb.get("standard.Performance_Gls"), "fbref")
    _set("assists_fbref", fb.get("standard.Performance_Ast"), "fbref")
    _set("fouls_committed", fb.get("misc.Performance_Fls"), "fbref")
    _set("tackles_won", fb.get("misc.Performance_TklW"), "fbref")
    _set("interceptions_fbref", fb.get("misc.Performance_Int"), "fbref")

    # --- FootyStats (aerial duels, historical depth, dribbles) ---
    fs = result.sources.get("footystats") or {}
    cs = fs.get("current_season") or {}
    _set("aerial_duels_won", cs.get("aerial_duels_won"), "footystats")
    _set("ground_duels_won", cs.get("ground_duels_won"), "footystats")
    _set("dribbles", cs.get("dribbles"), "footystats")
    _set("fouls_committed_fs", cs.get("fouls_committed"), "footystats")
    _set("shots_footystats", cs.get("shots"), "footystats")
    _set("xg_footystats", cs.get("xg"), "footystats")
    _set("npxg_footystats", cs.get("npxg"), "footystats")
    _set("xa_footystats", cs.get("xa"), "footystats")
    _set("minutes_footystats", cs.get("minutes"), "footystats")
    _set("matches", cs.get("matches"), "footystats")

    # --- one-versus-one (progressive carries, ball regains, duels) ---
    ovo = result.sources.get("ovo") or {}
    stats_ovo = ovo.get("stats") or {}
    _set("progressive_carries", stats_ovo.get("progressive_carries"), "ovo")
    _set("passes_to_opp_box", stats_ovo.get("passes_to_opp_box"), "ovo")
    _set("shots_on_goal_ovo", stats_ovo.get("shots_on_goal"), "ovo")
    _set("ball_regains", stats_ovo.get("ball_regains"), "ovo")
    _set("ball_losses_pct", stats_ovo.get("ball_losses_pct"), "ovo")
    _set("ground_duels_won", stats_ovo.get("ground_duels_won"), "ovo")
    _set("ground_duels_lost", stats_ovo.get("ground_duels_lost"), "ovo")
    _set("aerial_duels_won", stats_ovo.get("aerial_duels_won"), "ovo")
    _set("offensive_touches", stats_ovo.get("offensive_touches"), "ovo")
    _set("index_overall", stats_ovo.get("index_overall"), "ovo")
    _set("pass_accuracy_pct", stats_ovo.get("pass_accuracy_pct"), "ovo")

    return merged


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get("/{name}/profile", response_model=ProfileResponse)
def get_player_profile(name: str) -> ProfileResponse:
    try:
        registry = _load_registry()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load player registry: {exc}")

    try:
        result = fetch_profile(name, registry, _CACHE_DIR)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    merged = _merge_stats(result)

    # Strip non-serialisable objects from raw sources
    raw: dict[str, Any] = {}
    for source, data in result.sources.items():
        if data is not None:
            # Coerce numpy/pandas types to native Python for JSON serialisation
            raw[source] = _make_serialisable(data)

    return ProfileResponse(
        player=result.player,
        display_name=result.display_name,
        position=result.position,
        team=result.team,
        available_sources=result.available_sources,
        errors=result.errors,
        merged=merged,
        raw=raw,
    )


def _make_serialisable(obj: Any) -> Any:
    """Recursively coerce numpy/pandas scalar types to native Python."""
    if isinstance(obj, dict):
        return {k: _make_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serialisable(v) for v in obj]
    try:
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
    except ImportError:
        pass
    return obj
