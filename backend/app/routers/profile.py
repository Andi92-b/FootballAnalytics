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

    # --- Sofascore ---
    ss = result.sources.get("sofascore") or {}
    _set("rating",                   ss.get("rating"),                          "sofascore")
    _set("goals",                    ss.get("goals"),                           "sofascore")
    _set("assists",                  ss.get("assists"),                         "sofascore")
    _set("xa",                       ss.get("expectedAssists"),                 "sofascore")
    _set("xg_sc",                    ss.get("expectedGoals"),                   "sofascore")
    _set("goals_assists_sum",        ss.get("goalsAssistsSum"),                 "sofascore")
    _set("headed_goals",             ss.get("headedGoals"),                     "sofascore")
    _set("goals_inside_box",         ss.get("goalsFromInsideTheBox"),           "sofascore")
    _set("goals_outside_box",        ss.get("goalsFromOutsideTheBox"),          "sofascore")
    _set("hit_woodwork",             ss.get("hitWoodwork"),                     "sofascore")
    _set("goal_conversion_pct",      ss.get("goalConversionPercentage"),        "sofascore")
    _set("penalty_won",              ss.get("penaltyWon"),                      "sofascore")
    _set("big_chances_created",      ss.get("bigChancesCreated"),               "sofascore")
    _set("big_chances_missed",       ss.get("bigChancesMissed"),                "sofascore")
    # Shots
    _set("total_shots",              ss.get("totalShots"),                      "sofascore")
    _set("shots_on_target",          ss.get("shotsOnTarget"),                   "sofascore")
    _set("shots_off_target",         ss.get("shotsOffTarget"),                  "sofascore")
    _set("shots_inside_box",         ss.get("shotsFromInsideTheBox"),           "sofascore")
    _set("shots_outside_box",        ss.get("shotsFromOutsideTheBox"),          "sofascore")
    _set("blocked_shots",            ss.get("blockedShots"),                    "sofascore")
    # Passing
    _set("total_passes",             ss.get("totalPasses"),                     "sofascore")
    _set("pass_accuracy_pct",        ss.get("accuratePassesPercentage"),        "sofascore")
    _set("passes_own_half",          ss.get("accurateOwnHalfPasses"),           "sofascore")
    _set("passes_opp_half",          ss.get("accurateOppositionHalfPasses"),    "sofascore")
    _set("passes_final_third",       ss.get("accurateFinalThirdPasses"),        "sofascore")
    _set("key_passes",               ss.get("keyPasses"),                       "sofascore")
    _set("pass_to_assist",           ss.get("passToAssist"),                    "sofascore")
    _set("accurate_long_balls",      ss.get("accurateLongBalls"),               "sofascore")
    _set("accurate_long_balls_pct",  ss.get("accurateLongBallsPercentage"),     "sofascore")
    _set("accurate_crosses",         ss.get("accurateCrosses"),                 "sofascore")
    _set("cross_accuracy_pct",       ss.get("accurateCrossesPercentage"),       "sofascore")
    _set("total_crosses",            ss.get("totalCross"),                      "sofascore")
    _set("total_long_balls",         ss.get("totalLongBalls"),                  "sofascore")
    # Dribbling
    _set("successful_dribbles",      ss.get("successfulDribbles"),              "sofascore")
    _set("dribble_success_pct",      ss.get("successfulDribblesPercentage"),    "sofascore")
    _set("dispossessed",             ss.get("dispossessed"),                    "sofascore")
    _set("dribbled_past",            ss.get("dribbledPast"),                    "sofascore")
    # Defending
    _set("tackles",                  ss.get("tackles"),                         "sofascore")
    _set("tackles_won_sc",           ss.get("tacklesWon"),                      "sofascore")
    _set("tackles_won_pct",          ss.get("tacklesWonPercentage"),            "sofascore")
    _set("interceptions",            ss.get("interceptions"),                   "sofascore")
    _set("ground_duels_won",         ss.get("groundDuelsWon"),                  "sofascore")
    _set("ground_duels_won_pct",     ss.get("groundDuelsWonPercentage"),        "sofascore")
    _set("aerial_duels_won",         ss.get("aerialDuelsWon"),                  "sofascore")
    _set("aerial_duels_won_pct",     ss.get("aerialDuelsWonPercentage"),        "sofascore")
    _set("aerial_duels_lost",        ss.get("aerialLost"),                      "sofascore")
    _set("total_duels_won",          ss.get("totalDuelsWon"),                   "sofascore")
    _set("total_duels_won_pct",      ss.get("totalDuelsWonPercentage"),         "sofascore")
    _set("duels_lost",               ss.get("duelLost"),                        "sofascore")
    _set("ball_recovery",            ss.get("ballRecovery"),                    "sofascore")
    _set("possession_lost",          ss.get("possessionLost"),                  "sofascore")
    _set("possession_won_att_third", ss.get("possessionWonAttThird"),           "sofascore")
    _set("fouls_sc",                 ss.get("fouls"),                           "sofascore")
    _set("was_fouled",               ss.get("wasFouled"),                       "sofascore")
    _set("yellow_cards",             ss.get("yellowCards"),                     "sofascore")
    _set("red_cards",                ss.get("redCards"),                        "sofascore")
    _set("offsides",                 ss.get("offsides"),                        "sofascore")
    _set("touches",                  ss.get("touches"),                         "sofascore")
    _set("appearances",              ss.get("appearances"),                     "sofascore")
    _set("matches_started",          ss.get("matchesStarted"),                  "sofascore")
    _set("minutes_sc",               ss.get("minutesPlayed"),                   "sofascore")
    _set("totw_appearances",         ss.get("totwAppearances"),                 "sofascore")
    _set("scoring_frequency",        ss.get("scoringFrequency"),                "sofascore")

    # --- Understat ---
    us = result.sources.get("understat") or {}
    _set("npxg",            us.get("npxG"),  "understat")
    _set("xg",              us.get("xG"),    "understat")
    _set("shots_understat", us.get("shots"), "understat")

    # --- FBref ---
    fb = result.sources.get("fbref") or {}
    _set("minutes",             fb.get("standard.Playing Time_Min"),      "fbref")
    _set("matches_played",      fb.get("standard.Playing Time_MP"),       "fbref")
    _set("matches_started_fb",  fb.get("standard.Playing Time_Starts"),   "fbref")
    _set("goals_fbref",         fb.get("standard.Performance_Gls"),       "fbref")
    _set("assists_fbref",       fb.get("standard.Performance_Ast"),       "fbref")
    _set("goals_no_pen",        fb.get("standard.Performance_G-PK"),      "fbref")
    _set("yellow_cards_fbref",  fb.get("standard.Performance_CrdY"),      "fbref")
    _set("red_cards_fbref",     fb.get("standard.Performance_CrdR"),      "fbref")
    _set("goals_per90",         fb.get("standard.Per 90 Minutes_Gls"),    "fbref")
    _set("assists_per90",       fb.get("standard.Per 90 Minutes_Ast"),    "fbref")
    _set("ga_per90",            fb.get("standard.Per 90 Minutes_G+A"),    "fbref")
    _set("shots_fbref",         fb.get("shooting.Standard_Sh"),           "fbref")
    _set("shots_on_target_fbref", fb.get("shooting.Standard_SoT"),        "fbref")
    _set("shots_on_target_pct", fb.get("shooting.Standard_SoT%"),         "fbref")
    _set("shots_per90",         fb.get("shooting.Standard_Sh/90"),        "fbref")
    _set("goal_per_shot",       fb.get("shooting.Standard_G/Sh"),         "fbref")
    _set("goal_per_sot",        fb.get("shooting.Standard_G/SoT"),        "fbref")
    _set("fouls_committed",     fb.get("misc.Performance_Fls"),           "fbref")
    _set("fouls_drawn_fbref",   fb.get("misc.Performance_Fld"),           "fbref")
    _set("offsides_fbref",      fb.get("misc.Performance_Off"),           "fbref")
    _set("crosses_fbref",       fb.get("misc.Performance_Crs"),           "fbref")
    _set("tackles_won",         fb.get("misc.Performance_TklW"),          "fbref")
    _set("interceptions_fbref", fb.get("misc.Performance_Int"),           "fbref")

    # --- FootyStats ---
    fs = result.sources.get("footystats") or {}
    cs = fs.get("current_season") or {}
    _set("aerial_duels_won_fs",  cs.get("aerial_duels_won"),  "footystats")
    _set("ground_duels_won_fs",  cs.get("ground_duels_won"),  "footystats")
    _set("dribbles_fs",          cs.get("dribbles"),          "footystats")
    _set("fouls_committed_fs",   cs.get("fouls_committed"),   "footystats")
    _set("shots_footystats",     cs.get("shots"),             "footystats")
    _set("xg_footystats",        cs.get("xg"),                "footystats")
    _set("npxg_footystats",      cs.get("npxg"),              "footystats")
    _set("xa_footystats",        cs.get("xa"),                "footystats")
    _set("minutes_footystats",   cs.get("minutes"),           "footystats")
    _set("matches_fs",           cs.get("matches"),           "footystats")

    # --- one-versus-one ---
    ovo = result.sources.get("ovo") or {}
    s = ovo.get("stats") or {}
    _set("progressive_carries",      s.get("progressive_carries"),      "ovo")
    _set("passes_to_opp_box",        s.get("passes_to_opp_box"),        "ovo")
    _set("passes_to_final_third_ovo",s.get("passes_to_final_third_ovo"),"ovo")
    _set("shots_on_goal_ovo",        s.get("shots_on_goal"),            "ovo")
    _set("chances_created_ovo",      s.get("chances_created_ovo"),      "ovo")
    _set("goals_headed_ovo",         s.get("goals_headed_ovo"),         "ovo")
    _set("goals_foot_ovo",           s.get("goals_foot_ovo"),           "ovo")
    _set("goals_long_distance",      s.get("goals_long_distance"),      "ovo")
    _set("scorer_points_per_game",   s.get("scorer_points_per_game"),   "ovo")
    _set("offensive_touches",        s.get("offensive_touches"),        "ovo")
    _set("defensive_touches_oop",    s.get("defensive_touches_oop"),    "ovo")
    _set("passes_low_total",         s.get("passes_low_total"),         "ovo")
    _set("passes_low_pct",           s.get("passes_low_pct"),           "ovo")
    _set("ball_losses_total",        s.get("ball_losses_total"),        "ovo")
    _set("ball_losses_pct",          s.get("ball_losses_pct"),          "ovo")
    _set("ball_losses_opp_box",      s.get("ball_losses_opp_box"),      "ovo")
    _set("ball_regains",             s.get("ball_regains"),             "ovo")
    _set("ball_regains_opp_box",     s.get("ball_regains_opp_box"),     "ovo")
    _set("ground_duels_won",         s.get("ground_duels_won"),         "ovo")
    _set("ground_duels_lost",        s.get("ground_duels_lost"),        "ovo")
    _set("ground_duels_won_pct",     s.get("ground_duels_won_pct"),     "ovo")
    _set("aerial_duels_won",         s.get("aerial_duels_won"),         "ovo")
    _set("aerial_duels_lost",        s.get("aerial_duels_lost"),        "ovo")
    _set("aerial_duels_won_pct",     s.get("aerial_duels_won_pct"),     "ovo")
    _set("clearances_head",          s.get("clearances_head"),          "ovo")
    _set("clearances_foot",          s.get("clearances_foot"),          "ovo")
    _set("tackles_ovo",              s.get("tackles_ovo"),              "ovo")
    _set("index_overall",            s.get("index_overall"),            "ovo")
    _set("index_defensive",          s.get("index_defensive"),          "ovo")
    _set("index_offensive",          s.get("index_offensive"),          "ovo")
    _set("offensive_interventions",  s.get("offensive_interventions"),  "ovo")
    _set("successful_dribbles_ovo",  s.get("successful_dribbles_ovo"),  "ovo")

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
