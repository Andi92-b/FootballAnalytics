from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api")


class MetricResult(BaseModel):
    name: str
    category: str
    raw: float
    percentile: int


class PlayerResponse(BaseModel):
    player: str
    position: str
    season: str
    league: str
    metrics: list[MetricResult]
    svg: str


@router.get("/player/{name}", response_model=PlayerResponse)
async def get_player(
    name: str,
    season: int = Query(default=2024, description="Season start year, e.g. 2024 for 2024-25"),
    league: str = Query(default="ENG-Premier League", description="soccerdata league ID"),
) -> PlayerResponse:
    """Return pizza chart data for a player."""
    from backend.app.services import data_service, chart_service

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
        metrics=[
            MetricResult(name=m.name, category=m.category, raw=m.raw, percentile=m.percentile)
            for m in pizza_data.metrics
        ],
        svg=svg,
    )
