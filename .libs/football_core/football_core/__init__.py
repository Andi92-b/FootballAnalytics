"""
football_core — public API

Skills and backend services import from here. Do not import sub-modules directly.
"""

from football_core.fetcher import fetch_tables, get_player_row, merge_player_stats
from football_core.metrics import compute_metric_values
from football_core.percentiles import map_position, get_position_profile, compute_percentiles
from football_core.renderer import render_pizza

__all__ = [
    "fetch_tables",
    "get_player_row",
    "merge_player_stats",
    "compute_metric_values",
    "map_position",
    "get_position_profile",
    "compute_percentiles",
    "render_pizza",
]
