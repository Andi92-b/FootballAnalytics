"""data_service — orchestrates fetch + percentile computation."""
from pathlib import Path

from football_core.fetcher import fetch_tables, merge_player_stats, add_team_poss
from football_core.percentiles import map_position, compute_percentiles
from football_core.models import PizzaData

_CACHE_DIR = Path(__file__).parents[3] / ".cache" / "fbref"
_SD_TABLES = ["standard", "shooting", "misc"]


def get_pizza_data(player_name: str, season: int, league: str) -> PizzaData:
    """Fetch player stats and compute percentiles. Returns PizzaData."""
    from fastapi import HTTPException
    try:
        tables = fetch_tables(league, season, _CACHE_DIR, tables=_SD_TABLES)
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Season {season} data not available for {league}. "
                   f"Only completed seasons are supported. ({exc})",
        ) from exc
    tables = add_team_poss(tables)

    std = tables["standard"]
    pc = next(c for c in std.columns if str(c).lower() == "player")
    all_names = std[pc].dropna().unique().tolist()
    all_player_stats = [s for s in (merge_player_stats(n, tables) for n in all_names) if s]

    stats = merge_player_stats(player_name, tables)
    if not stats:
        return None

    pos_raw = stats.get("standard.pos", "DF")
    pos_bucket = map_position(pos_raw.split(",")[0].strip())
    results = compute_percentiles(stats, all_player_stats, pos_bucket)

    season_label = f"{season}-{str(season + 1)[-2:]}"
    return PizzaData(
        player=player_name,
        position=pos_bucket,
        season=season_label,
        league=league,
        metrics=results,
    )
