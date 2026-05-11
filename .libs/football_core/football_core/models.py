"""
models.py — Pydantic data models shared across the pipeline.

Models:
  PlayerStats     — raw per-player stat dict keyed by "<table>.<column>"
  MetricResult    — one computed metric: name, category, raw value, percentile rank
  PositionProfile — position bucket + ordered metric list for a position
  PizzaData       — full pipeline output: player metadata + metrics + svg string
"""

# Implementation: define Pydantic BaseModel classes for each model above.
# MetricResult.category must be a Literal["Defence","Possession","Progression","Attack"].
# PizzaData.svg is optional (None before render-pizza runs).
