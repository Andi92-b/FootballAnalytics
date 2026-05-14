from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import json
from pathlib import Path

from backend import db as player_db

router = APIRouter(prefix="/api")

_REGISTRY_PATH = Path(__file__).parents[3] / "player_registry.json"


class PlayerSearchResult(BaseModel):
    name: str
    team: str
    league: str
    position: str
    season: int
    minutes: int


@router.get("/players/search", response_model=list[PlayerSearchResult])
async def search_players(
    q: str = Query(..., min_length=2, description="Name fragment to search"),
    limit: int = Query(default=10, le=30),
) -> list[PlayerSearchResult]:
    """Fuzzy name search across all indexed players."""
    results = player_db.search_players(q, limit)
    return [PlayerSearchResult(**r) for r in results]


class MetricResult(BaseModel):
    name: str
    category: str
    raw: float
    percentile: int
    source: str = "fbref"

class PeerEntry(BaseModel):
    name: str
    team: str
    position: str
    minutes: int
    metric_values: dict[str, float]


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
    peers: list[PeerEntry] = []


class PlayerSeasonsResponse(BaseModel):
    player: str
    display_name: str
    league: str  # current/default league
    position: str
    team: str
    seasons: list[int]
    seasons_info: list[dict]  # [{season: int, league: str}, ...]


@router.get("/player/{name}/seasons", response_model=PlayerSeasonsResponse)
async def get_player_seasons(name: str) -> PlayerSeasonsResponse:
    """Return the available seasons and league for a player.

    First checks player_registry.json (rich metadata), then falls back to the
    SQLite player index (FBref-only, current season only).
    """
    # ── 1. Registry lookup (rich metadata) ──────────────────────────────────
    try:
        registry = json.loads(_REGISTRY_PATH.read_text())
    except Exception:
        registry = {}

    entry = registry.get(name) or next(
        (v for k, v in registry.items() if k.lower() == name.lower()), None
    )

    if entry is not None:
        current_league: str = entry.get("fbref_league", "GER-Bundesliga")
        current_season: int = entry.get("fbref_season", 2025)
        league_history: dict = entry.get("league_history", {})
        if league_history:
            seasons_info = [
                {"season": int(yr), "league": lg}
                for yr, lg in sorted(league_history.items(), key=lambda x: int(x[0]))
            ]
            seasons = [s["season"] for s in seasons_info]
        else:
            seasons = list(range(current_season - 4, current_season + 1))
            seasons_info = [{"season": yr, "league": current_league} for yr in seasons]
        return PlayerSeasonsResponse(
            player=name,
            display_name=entry.get("display_name", name),
            league=current_league,
            position=entry.get("position", ""),
            team=entry.get("current_team", ""),
            seasons=seasons,
            seasons_info=seasons_info,
        )

    # ── 2. DB fallback (any FBref player) ────────────────────────────────────
    db_seasons = player_db.get_player_seasons(name)
    if not db_seasons:
        raise HTTPException(
            status_code=404,
            detail=f"Player '{name}' not found. Use /api/players/search?q=... to find players.",
        )
    # Use the entry with the most minutes as the canonical league
    primary = max(db_seasons, key=lambda r: r["minutes"])
    seasons_info = [{"season": r["season"], "league": r["league"]} for r in db_seasons]
    seasons = [r["season"] for r in db_seasons]
    return PlayerSeasonsResponse(
        player=primary["name"],   # exact FBref name from DB
        display_name=primary["name"],
        league=primary["league"],
        position=primary["position"] or "",
        team=primary["team"] or "",
        seasons=seasons,
        seasons_info=seasons_info,
    )


@router.get("/player/{name}", response_model=PlayerResponse)
async def get_player(
    name: str,
    season: int = Query(default=2025, description="Season start year, e.g. 2025 for 2025-26"),
    league: str = Query(default="", description="soccerdata league ID — auto-detected from registry if omitted"),
) -> PlayerResponse:
    """Return pizza chart data for a player."""
    from backend.app.services import data_service, chart_service

    # Auto-detect league from registry then DB fallback
    if not league:
        try:
            registry = json.loads(_REGISTRY_PATH.read_text())
            entry = registry.get(name) or next(
                (v for k, v in registry.items() if k.lower() == name.lower()), None
            )
            if entry:
                league = entry.get("fbref_league", "")
        except Exception:
            pass
        if not league:
            db_entry = player_db.get_player_entry(name)
            if db_entry:
                league = db_entry["league"]
        if not league:
            league = "ENG-Premier League"

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
        peers=[
            PeerEntry(
                name=p.name, team=p.team, position=p.position,
                minutes=p.minutes, metric_values=p.metric_values,
            )
            for p in pizza_data.peers
        ],
    )
