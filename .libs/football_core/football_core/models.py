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
