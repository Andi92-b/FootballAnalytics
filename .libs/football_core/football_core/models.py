"""
models.py — Pydantic data models shared across the pipeline.
"""

from typing import Literal

from pydantic import BaseModel


class MetricResult(BaseModel):
    name: str
    category: Literal["Defence", "Possession", "Progression", "Attack"]
    raw: float
    percentile: int  # 0–99
    source: str = "fbref"  # e.g. "fbref", "fbref+understat", "whoscored", "pending"


class PeerEntry(BaseModel):
    name: str
    team: str
    position: str       # effective position bucket, e.g. "W", "CF", "CB"
    apps: int = 0       # matches played
    starts: int = 0     # games started
    minutes: int
    metric_values: dict[str, float]      # metric_name → raw value
    metric_percentiles: dict[str, int] = {}  # metric_name → 0-99 percentile within peer group
    tm_main_position: str = ""           # TM main position string, e.g. "Left Winger"
    tm_other_positions: list[str] = []   # TM other positions, e.g. ["Right Winger", "Centre-Forward"]


class SimilarPlayer(BaseModel):
    name: str
    team: str
    position: str       # position bucket, e.g. "W"
    minutes: int
    similarity: float   # 1 − mean(|Δpercentile|)/99; higher = more similar
    mean_deviation: float  # mean absolute percentile deviation (0–99 scale)
    metric_values: dict[str, float]


class PositionProfile(BaseModel):
    position_bucket: str
    fbref_string: str
    metrics: list[dict]  # [{"name": str, "category": str}, ...]


class PlayingTimeStats(BaseModel):
    """Season-level playing time breakdown from the FBref playing_time table."""
    pos: str              # raw FBref position string, e.g. "FW,MF"
    mp: int               # matches played
    minutes: int          # total minutes
    min_pct: float        # % of available league minutes played
    starts: int           # games started
    mins_per_start: int   # avg minutes when starting
    complete_games: int   # games where player played full 90+
    subs: int             # games entered as substitute
    mins_per_sub: int     # avg minutes when coming on as sub
    unsubbed: int         # games where player was NOT substituted off


class PizzaData(BaseModel):
    player: str
    position: str
    season: str
    league: str
    metrics: list[MetricResult]
    missing_metrics: list[str] = []
    data_sources: list[str] = []
    data_freshness: dict[str, str] = {}
    svg: str | None = None
    peers: list[PeerEntry] = []
    similar_players: list[SimilarPlayer] = []
    playing_time: PlayingTimeStats | None = None
    raw_stats: dict[str, float] = {}  # counting stats: goals, assists, shots, etc.
    tm_main_position: str = ""
    tm_other_positions: list[str] = []
