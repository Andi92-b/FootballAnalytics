from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import json
from pathlib import Path

router = APIRouter(prefix="/api")

_REGISTRY_PATH = Path(__file__).parents[3] / "player_registry.json"


class MetricResult(BaseModel):
    name: str
    category: str
    raw: float
    percentile: int
    source: str = "fbref"


class PlayerResponse(BaseModel):
    player: str
    position: str
    season: str
    league: str
    data_sources: list[str] = []
    missing_metrics: list[str] = []
    data_freshness: dict[str, str] = {}
    metrics: list[MetricResult]
    svg: str


class PlayerSeasonsResponse(BaseModel):
    player: str
    display_name: str
    league: str
    position: str
    team: str
    seasons: list[int]


@router.get("/player/{name}/seasons", response_model=PlayerSeasonsResponse)
async def get_player_seasons(name: str) -> PlayerSeasonsResponse:
    """Return the available seasons and league for a registry player."""
    try:
        registry = json.loads(_REGISTRY_PATH.read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not read player registry") from exc

    entry = registry.get(name)
    if entry is None:
        # Try case-insensitive match
        lower = name.lower()
        entry = next((v for k, v in registry.items() if k.lower() == lower), None)
        if entry is None:
            known = list(registry.keys())
            raise HTTPException(
                status_code=404,
                detail=f"Player '{name}' not found in registry. Known players: {known}",
            )

    current_season: int = entry.get("fbref_season", 2025)
    seasons = list(range(current_season - 4, current_season + 1))  # last 5 seasons

    return PlayerSeasonsResponse(
        player=name,
        display_name=entry.get("display_name", name),
        league=entry.get("fbref_league", "GER-Bundesliga"),
        position=entry.get("position", ""),
        team=entry.get("current_team", ""),
        seasons=seasons,
    )


@router.get("/player/{name}", response_model=PlayerResponse)
async def get_player(
    name: str,
    season: int = Query(default=2025, description="Season start year, e.g. 2025 for 2025-26"),
    league: str = Query(default="", description="soccerdata league ID — auto-detected from registry if omitted"),
) -> PlayerResponse:
    """Return pizza chart data for a player."""
    from backend.app.services import data_service, chart_service

    # Auto-detect league from registry when not provided
    if not league:
        try:
            registry = json.loads(_REGISTRY_PATH.read_text())
            entry = registry.get(name) or next(
                (v for k, v in registry.items() if k.lower() == name.lower()), None
            )
            if entry:
                league = entry.get("fbref_league", "GER-Bundesliga")
        except Exception:
            pass
        if not league:
            league = "GER-Bundesliga"

    pizza_data = data_service.get_pizza_data(name, season, league)
    if pizza_data is None:
        raise HTTPException(status_code=404, detail=f"Player '{name}' not found in {league} {season}")

    svg = chart_service.render(pizza_data)
    pizza_data.svg = svg

    return PlayerResponse(
        player=pizza_data.player,
        position=pizza_data.position,
        season=pizza_data.season,
        league=pizza_data.league,
        data_sources=pizza_data.data_sources,
        missing_metrics=pizza_data.missing_metrics,
        data_freshness=pizza_data.data_freshness,
        metrics=[
            MetricResult(
                name=m.name, category=m.category,
                raw=m.raw, percentile=m.percentile, source=m.source,
            )
            for m in pizza_data.metrics
        ],
        svg=svg,
    )
