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
    # TODO: implement via data_service + chart_service (player-endpoint skill)
    raise HTTPException(status_code=501, detail="Not implemented yet")
