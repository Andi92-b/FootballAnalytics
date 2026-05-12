"""
pipeline.py — Orchestrates the three-tier data fetch pipeline.

Tier A: FBref (basic stats — always attempted)
Tier B: Understat (xG / xA — Big-5 leagues only)
Tier C: WhoScored (advanced stats — stub/degraded in V1)

Returns a FetchResult with:
  - fbref_tables      : dict[str, DataFrame]
  - available_sources : list of source names that returned data
  - data_freshness    : dict mapping source → ISO date string (cache mtime or today)
  - understat_data    : dict[normalised_name → {npxG, xA, ...}] or None
  - whoscored_data    : dict[normalised_name → {...}] or None
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from football_core.sources.fbref import fetch_fbref
from football_core.sources.understat import fetch_understat
from football_core.sources.whoscored import fetch_whoscored

log = logging.getLogger(__name__)


@dataclass
class FetchResult:
    fbref_tables: dict[str, pd.DataFrame]
    available_sources: list[str]
    data_freshness: dict[str, str]
    understat_data: dict[str, dict] | None = None
    whoscored_data: dict[str, dict] | None = None


def fetch_all(
    league: str,
    season: int,
    cache_dir: Path,
    force_refresh: bool = False,
) -> FetchResult:
    """
    Run all three fetch tiers, returning a FetchResult.

    Tier B and C failures are caught silently — the pipeline proceeds in degraded mode.
    """
    today = datetime.date.today().isoformat()
    available_sources: list[str] = []
    freshness: dict[str, str] = {}

    # ── Tier A: FBref ─────────────────────────────────────────────────────────
    fbref_tables = fetch_fbref(league, season, cache_dir, force_refresh=force_refresh)
    if fbref_tables:
        available_sources.append("fbref")
        freshness["fbref"] = today

    # ── Tier B: Understat ─────────────────────────────────────────────────────
    understat_data: dict[str, dict] | None = None
    try:
        understat_data = fetch_understat(league, season, cache_dir, force_refresh=force_refresh)
        if understat_data is not None:
            available_sources.append("understat")
            freshness["understat"] = today
    except Exception as exc:
        log.warning("Understat tier failed: %s", exc)

    # ── Tier C: WhoScored ─────────────────────────────────────────────────────
    whoscored_data: dict[str, dict] | None = None
    try:
        whoscored_data = fetch_whoscored(league, season, cache_dir, force_refresh=force_refresh)
        if whoscored_data is not None:
            available_sources.append("whoscored")
            freshness["whoscored"] = today
    except Exception as exc:
        log.warning("WhoScored tier failed: %s", exc)

    log.info("Pipeline complete — sources available: %s", available_sources)
    return FetchResult(
        fbref_tables=fbref_tables,
        available_sources=available_sources,
        data_freshness=freshness,
        understat_data=understat_data,
        whoscored_data=whoscored_data,
    )
