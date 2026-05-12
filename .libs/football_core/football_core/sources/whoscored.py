"""
sources/whoscored.py — Tier C: advanced stats via WhoScored.

STATUS: STUB — V1 returns None (degraded mode).

WhoScored blocks simple HTTP requests and requires Selenium + undetected-chromedriver.
This interface is defined so the merger and pipeline can reference it without breaking.
All WhoScored-dependent metrics go into missing_metrics until this stub is promoted.

Interface contract (for future implementation):
    fetch_whoscored(league, season, cache_dir) -> dict[str, dict] | None

    Return value (per player, keyed by normalised name):
    {
        "touches": float,
        "att_third_touches": float,
        "att_pen_touches": float,
        "mid_third_touches": float,
        "dribbles_att": float,
        "crosses": float,
        "carries": float,
        "tackle_success_pct": float,
        "blocked_shots": float,
    }

Degraded mode: return None → pipeline records "whoscored" as unavailable →
  all Tier-C metrics added to missing_metrics.
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def fetch_whoscored(
    league: str,
    season: int,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict[str, dict] | None:
    """
    Fetch advanced stats from WhoScored.

    V1: always returns None (stub / degraded mode).
    """
    log.info(
        "WhoScored: stub active — Tier C unavailable for %s %s (degraded mode)", league, season
    )
    return None
