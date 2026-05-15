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
    apps: int = 0
    starts: int = 0
    minutes: int
    metric_values: dict[str, float]
    metric_percentiles: dict[str, int] = {}
    tm_main_position: str = ""
    tm_other_positions: list[str] = []


class SimilarPlayer(BaseModel):
    name: str
    team: str
    position: str
    minutes: int
    similarity: float
    mean_deviation: float
    metric_values: dict[str, float]


class PlayingTimeStats(BaseModel):
    pos: str
    mp: int
    minutes: int
    min_pct: float
    starts: int
    mins_per_start: int
    complete_games: int
    subs: int
    mins_per_sub: int
    unsubbed: int


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
    similar_players: list[SimilarPlayer] = []
    playing_time: PlayingTimeStats | None = None
    raw_stats: dict = {}
    tm_main_position: str = ""
    tm_other_positions: list[str] = []


class PlayerSeasonsResponse(BaseModel):
    player: str
    display_name: str
    league: str  # current/default league
    position: str
    team: str
    seasons: list[int]
    seasons_info: list[dict]  # [{season: int, league: str}, ...]
    sofascore_id: int | None = None
    sofascore_slug: str = ""


class SeasonDataPoint(BaseModel):
    season: int
    season_label: str   # "2024-25"
    league: str
    overall_score: int
    category_scores: dict[str, int]  # {"Defence": 72, ...}
    raw_kpis: dict


class PlayerHistoryResponse(BaseModel):
    player: str
    history: list[SeasonDataPoint]


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
        # Build a URL-safe Sofascore slug from display_name
        import unicodedata, re as _re
        raw_name = entry.get("display_name", name)
        slug = unicodedata.normalize("NFD", raw_name).encode("ascii", "ignore").decode().lower()
        slug = _re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        return PlayerSeasonsResponse(
            player=name,
            display_name=raw_name,
            league=current_league,
            position=entry.get("position", ""),
            team=entry.get("current_team", ""),
            seasons=seasons,
            seasons_info=seasons_info,
            sofascore_id=entry.get("sofascore_id") or None,
            sofascore_slug=slug,
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


@router.get("/player/{name}/history", response_model=PlayerHistoryResponse)
async def get_player_history(name: str) -> PlayerHistoryResponse:
    """Return season-over-season performance scores for a player.

    Loops the player's league_history, calls get_pizza_data() per season
    (uses the existing SQLite cache), and computes overall + category scores
    from metric percentiles.  Capped at 6 seasons.
    """
    from backend.app.services import data_service

    try:
        registry = json.loads(_REGISTRY_PATH.read_text())
    except Exception:
        registry = {}

    entry = registry.get(name) or next(
        (v for k, v in registry.items() if k.lower() == name.lower()), None
    )
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Player '{name}' not found in registry")

    league_history: dict = entry.get("league_history", {})
    seasons_to_fetch = sorted(
        ((int(yr), lg) for yr, lg in league_history.items()),
        key=lambda x: x[0],
    )[-6:]  # last 6 seasons

    history: list[SeasonDataPoint] = []
    CATEGORIES = ["Defence", "Possession", "Progression", "Attack"]

    for season, league in seasons_to_fetch:
        try:
            pizza = data_service.get_pizza_data(name, season, league)
            if pizza is None or not pizza.metrics:
                continue
            all_pcts = [m.percentile for m in pizza.metrics]
            overall = round(sum(all_pcts) / len(all_pcts)) if all_pcts else 0
            cat_scores: dict[str, int] = {}
            for cat in CATEGORIES:
                pcts = [m.percentile for m in pizza.metrics if m.category == cat]
                cat_scores[cat] = round(sum(pcts) / len(pcts)) if pcts else 0
            raw_kpis = dict(pizza.raw_stats)
            if pizza.playing_time:
                pt = pizza.playing_time
                raw_kpis.update({
                    "minutes": pt.minutes,
                    "apps": pt.mp,
                    "starts": pt.starts,
                    "min_pct": pt.min_pct,
                    "complete_games": pt.complete_games,
                })
            history.append(SeasonDataPoint(
                season=season,
                season_label=pizza.season,
                league=league,
                overall_score=overall,
                category_scores=cat_scores,
                raw_kpis=raw_kpis,
            ))
        except Exception:
            continue  # skip seasons with no data

    return PlayerHistoryResponse(player=name, history=history)


# ── Role endpoint ─────────────────────────────────────────────────────────────

class RoleResponse(BaseModel):
    role: str
    description: str
    cluster_id: int
    similar_players: list[dict]  # [{name, team}]


@router.get("/player/{name}/role", response_model=RoleResponse)
async def get_player_role(
    name: str,
    season: int = Query(default=2025),
    league: str = Query(default="ENG-Premier League"),
) -> RoleResponse:
    """Return the tactical role assigned to a player by the k-means clustering model."""
    role_data = player_db.get_player_role(name, league, season)
    if role_data is None:
        raise HTTPException(status_code=404, detail="Role not found for this player/season/league")
    peers = player_db.get_cluster_peers(role_data["cluster_id"], league, name, limit=5)
    return RoleResponse(
        role=role_data["role_label"],
        description=role_data["role_desc"],
        cluster_id=role_data["cluster_id"],
        similar_players=peers,
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
                apps=p.apps, starts=p.starts,
                minutes=p.minutes, metric_values=p.metric_values,
                metric_percentiles=p.metric_percentiles,
                tm_main_position=p.tm_main_position,
                tm_other_positions=p.tm_other_positions,
            )
            for p in pizza_data.peers
        ],
        similar_players=[
            SimilarPlayer(
                name=s.name, team=s.team, position=s.position,
                minutes=s.minutes, similarity=s.similarity,
                mean_deviation=s.mean_deviation,
                metric_values=s.metric_values,
            )
            for s in pizza_data.similar_players
        ],
        playing_time=(
            PlayingTimeStats(**pizza_data.playing_time.model_dump())
            if pizza_data.playing_time else None
        ),
        raw_stats=pizza_data.raw_stats,
        tm_main_position=pizza_data.tm_main_position,
        tm_other_positions=pizza_data.tm_other_positions,
    )
