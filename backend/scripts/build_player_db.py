#!/usr/bin/env python3
"""
build_player_db.py — Populate the SQLite player index from FBref standard stats.

Reads from the .cache/fbref/<league>/<season>/standard.json files.
For leagues not yet cached, fetches from FBref (slow, but cached afterwards).

Usage:
    .venv/bin/python -m backend.scripts.build_player_db
    # or with extra leagues:
    .venv/bin/python -m backend.scripts.build_player_db --all
"""
import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on the path when run directly
_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_ROOT))

from backend.db import init_db, upsert_players

CACHE_DIR = _ROOT / ".cache" / "fbref"
SEASON = 2025

# Currently cached leagues — fast (read from disk)
CACHED_LEAGUES: list[str] = [
    "ENG-Premier League",
    "GER-Bundesliga",
]

# Additional top-5 leagues — will fetch from FBref if not cached (slow, ~30s each)
EXTRA_LEAGUES: list[str] = [
    "ESP-La Liga",
    "ITA-Serie A",
    "FRA-Ligue 1",
]


def _cache_path(league: str, season: int) -> Path:
    safe = league.replace(" ", "_").replace("-", "_")
    return CACHE_DIR / safe / str(season) / "standard.json"


def _load_cached(league: str, season: int) -> list[dict] | None:
    p = _cache_path(league, season)
    if p.exists():
        return json.loads(p.read_text())
    return None


def _fetch_via_pipeline(league: str, season: int) -> list[dict] | None:
    """Fetch FBref standard stats and cache them, returns raw records."""
    from football_core.sources.fbref import fetch_fbref
    tables = fetch_fbref(league, season, _ROOT / ".cache", force_refresh=False)
    if not tables or "standard" not in tables:
        return None
    std = tables["standard"]
    pc = next((c for c in std.columns if str(c).lower() == "player"), None)
    if pc is None:
        return None
    return std.to_dict("records")


def _records_to_db_rows(records: list[dict], league: str, season: int) -> list[dict]:
    rows = []
    for r in records:
        name = r.get("player") or r.get("Player")
        if not name or str(name).strip() in ("", "Player"):
            continue
        team = r.get("team") or r.get("Squad") or ""
        pos = r.get("pos") or r.get("Pos") or ""
        # minutes: try several column name variants
        minutes = (
            r.get("Playing Time_Min")
            or r.get("Min")
            or r.get("playing_time_min")
            or 0
        )
        try:
            minutes = int(float(minutes or 0))
        except (TypeError, ValueError):
            minutes = 0

        rows.append({
            "name": str(name).strip(),
            "team": str(team).strip(),
            "league": league,
            "position": str(pos).strip(),
            "season": season,
            "minutes": minutes,
        })
    return rows


def build(leagues: list[str], season: int = SEASON) -> None:
    init_db()
    total = 0
    for league in leagues:
        print(f"  {league} {season}...", end=" ", flush=True)
        records = _load_cached(league, season)
        if records is None:
            print("not cached, fetching from FBref...", end=" ", flush=True)
            records = _fetch_via_pipeline(league, season)
        if records is None:
            print("FAILED (no data)")
            continue
        rows = _records_to_db_rows(records, league, season)
        upsert_players(rows)
        total += len(rows)
        print(f"{len(rows)} players")
    print(f"\nDone — {total} player-season rows in DB.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the player SQLite index")
    parser.add_argument("--all", action="store_true", help="Also fetch La Liga, Serie A, Ligue 1")
    parser.add_argument("--season", type=int, default=SEASON, help=f"Season start year (default {SEASON})")
    args = parser.parse_args()

    leagues = CACHED_LEAGUES + (EXTRA_LEAGUES if args.all else [])
    print(f"Building player DB for season {args.season}, {len(leagues)} league(s):")
    build(leagues, args.season)


if __name__ == "__main__":
    main()
