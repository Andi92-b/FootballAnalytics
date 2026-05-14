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
    position: str       # raw FBref position string, e.g. "MF,FW"
    minutes: int
    metric_values: dict[str, float]  # metric_name → raw value


class SimilarPlayer(BaseModel):
    name: str
    team: str
    position: str       # position bucket, e.g. "W"
    minutes: int
    similarity: float   # cosine similarity 0–1 (higher = more similar)
    metric_values: dict[str, float]


class PositionProfile(BaseModel):
    position_bucket: str
    fbref_string: str
    metrics: list[dict]  # [{"name": str, "category": str}, ...]


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
