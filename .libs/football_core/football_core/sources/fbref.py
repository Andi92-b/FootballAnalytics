"""
sources/fbref.py — Tier A: FBref basic stats via soccerdata.

Post-2026-01-20 coverage (Opta feed gone):
    standard, shooting, misc   — fully available
    passing, defense, possession — empty / bot-blocked

Only tables in SD_TABLES are fetched here. Everything else is Tier B/C.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
import soccerdata as sd
from soccerdata.fbref import FBREF_API, _parse_table
from lxml import html as lhtml

log = logging.getLogger(__name__)

SD_TABLES = ["standard", "shooting", "misc", "playing_time"]

_PAGE = {
    "standard": "stats",
    "shooting": "shooting",
    "misc": "misc",
    "playing_time": "playing_time",
}


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _cache_path(cache_dir: Path, league: str, season: int, table: str) -> Path:
    safe_league = league.replace(" ", "_").replace("-", "_")
    return cache_dir / "fbref" / safe_league / str(season) / f"{table}.json"


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    import re
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = ["_".join(str(c) for c in col).strip("_") for col in df.columns]
    new_cols = []
    for col in df.columns:
        m = re.match(r"^Unnamed: \d+_level_0_(.+)$", str(col))
        new_cols.append(m.group(1) if m else col)
    df.columns = new_cols
    return df


def _save_cache(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(path, orient="records", date_format="iso")


def _load_cache(path: Path) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_json(path, orient="records")
    return None


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_fbref(
    league: str,
    season: int,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    """
    Fetch (or load from cache) FBref basic stat tables for the given league/season.

    Returns a dict keyed by table name: {"standard": df, "shooting": df, "misc": df}
    """
    fbref = sd.FBref(leagues=league, seasons=season)
    result: dict[str, pd.DataFrame] = {}

    for table in SD_TABLES:
        path = _cache_path(cache_dir, league, season, table)
        if not force_refresh:
            cached = _load_cache(path)
            if cached is not None:
                log.info("Cache hit: %s", path)
                result[table] = cached
                continue

        log.info("Scraping FBref %s …", table)
        try:
            df = fbref.read_player_season_stats(stat_type=table)
            df = df.reset_index()
            df = _flatten_columns(df)
            _save_cache(df, path)
            result[table] = df
            time.sleep(4)
        except Exception as exc:
            log.warning("FBref scrape failed for %s/%s/%s: %s", league, season, table, exc)

    return result
