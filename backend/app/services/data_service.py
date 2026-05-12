"""data_service — orchestrates three-tier fetch + percentile computation."""
from pathlib import Path

from football_core.pipeline import fetch_all
from football_core.fetcher import merge_player_stats, add_team_poss
from football_core.sources.merger import merge_sources
from football_core.percentiles import map_position, compute_percentiles
from football_core.models import PizzaData

_CACHE_DIR = Path(__file__).parents[3] / ".cache"


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

    # Build all-player stats with all source tiers merged in
    all_player_stats = []
    for n in all_names:
        s = merge_player_stats(n, tables)
        if s:
            s = merge_sources(s, n, fetch_result.understat_data, fetch_result.whoscored_data)
            all_player_stats.append(s)

    stats = merge_player_stats(player_name, tables)
    if not stats:
        return None
    stats = merge_sources(stats, player_name, fetch_result.understat_data, fetch_result.whoscored_data)

    pos_raw = stats.get("standard.pos", "DF")
    pos_bucket = map_position(pos_raw.split(",")[0].strip())
    results, missing = compute_percentiles(
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
    )

