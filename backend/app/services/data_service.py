"""data_service — orchestrates three-tier fetch + percentile computation."""
from pathlib import Path
import json
import unicodedata

from football_core.pipeline import fetch_all
from football_core.fetcher import merge_player_stats, add_team_poss
from football_core.sources.merger import merge_sources
from football_core.percentiles import map_position, compute_percentiles
from football_core.models import PizzaData
from football_core.pipeline_profile import fetch_profile

_CACHE_DIR = Path(__file__).parents[3] / ".cache"
_REGISTRY_PATH = Path(__file__).parents[3] / "player_registry.json"


def _normalize_name(name: str) -> str:
    """Lowercase + strip accents for fuzzy name matching between FBref and Sofascore."""
    return unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode().lower()


def _inject_sc_league_stats(stats: dict, name: str, sc_lookup: dict, sc_lookup_norm: dict) -> dict:
    """Inject Sofascore league stats for one player (peer or target) into their stats dict."""
    sc = sc_lookup.get(name) or sc_lookup_norm.get(_normalize_name(name))
    if sc:
        for k, v in sc.items():
            if k != "_sofascore_id" and v is not None:
                stats.setdefault(f"sofascore.{k}", v)  # don't overwrite richer profile data
    return stats


def _inject_profile_sources(stats: dict, player_name: str) -> dict:
    """Inject Sofascore and OVO data into the FBref stats dict for the target player."""
    try:
        registry = json.loads(_REGISTRY_PATH.read_text())
    except Exception:
        return stats

    try:
        result = fetch_profile(player_name, registry, _CACHE_DIR)
    except (KeyError, Exception):
        return stats

    ss = result.sources.get("sofascore") or {}
    for k, v in ss.items():
        if v is not None:
            stats[f"sofascore.{k}"] = v

    ovo = result.sources.get("ovo") or {}
    for k, v in (ovo.get("stats") or {}).items():
        if v is not None:
            stats[f"ovo.{k}"] = v

    return stats


def get_pizza_data(player_name: str, season: int, league: str) -> PizzaData:
    """Fetch player stats from all available sources and compute percentiles."""
    from fastapi import HTTPException
    try:
        fetch_result = fetch_all(league, season, _CACHE_DIR)
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Season {season} data not available for {league}. "
                   f"Only completed seasons are supported. ({exc})",
        ) from exc

    tables = add_team_poss(fetch_result.fbref_tables)

    std = tables.get("standard")
    if std is None:
        raise HTTPException(status_code=422, detail=f"No FBref data for {league} {season}")

    pc = next(c for c in std.columns if str(c).lower() == "player")
    all_names = std[pc].dropna().unique().tolist()

    # Build name→stats lookups for Sofascore league data (exact + normalised)
    sc_league = fetch_result.sofascore_league_data or {}
    sc_lookup_norm = {_normalize_name(k): v for k, v in sc_league.items()}

    # Build all-player stats for the peer group — FBref + Understat + Sofascore league
    all_player_stats = []
    for n in all_names:
        s = merge_player_stats(n, tables)
        if s:
            s = merge_sources(s, n, fetch_result.understat_data, fetch_result.whoscored_data)
            s = _inject_sc_league_stats(s, n, sc_league, sc_lookup_norm)
            all_player_stats.append(s)

    stats = merge_player_stats(player_name, tables)
    if not stats:
        return None
    stats = merge_sources(stats, player_name, fetch_result.understat_data, fetch_result.whoscored_data)
    # Inject Sofascore league stats first (base layer), then richer profile data on top
    stats = _inject_sc_league_stats(stats, player_name, sc_league, sc_lookup_norm)
    # Enrich the target player with Sofascore + OVO data from the profile pipeline
    stats = _inject_profile_sources(stats, player_name)

    pos_raw = stats.get("standard.pos", "DF")
    pos_bucket = map_position(pos_raw)  # pass full string so POSITION_MAP_MULTI matches e.g. "MF,DF" → DM
    results, missing, peers, similar = compute_percentiles(
        stats, all_player_stats, pos_bucket,
        available_sources=fetch_result.available_sources,
    )

    season_label = f"{season}-{str(season + 1)[-2:]}"
    return PizzaData(
        player=player_name,
        position=pos_bucket,
        season=season_label,
        league=league,
        metrics=results,
        missing_metrics=missing,
        data_sources=fetch_result.available_sources,
        data_freshness=fetch_result.data_freshness,
        peers=peers,
        similar_players=similar,
    )

