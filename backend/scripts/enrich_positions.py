#!/usr/bin/env python3
"""
enrich_positions.py — Populate the player_positions table with canonical position data.

For each player in the `players` table:
  1. Check the Transfermarkt cache  →  use TM main + other positions (highest quality)
  2. Fall back to the FBref position string  →  map to position bucket via percentiles.map_position

The table is keyed by player name (UNIQUE) so this script is safe to re-run.
It only updates rows whose source changes from 'fbref' to 'transfermarkt' (upgrade), or
when the TM cache is newer than the last update.

Usage:
    .venv/bin/python -m backend.scripts.enrich_positions
    .venv/bin/python -m backend.scripts.enrich_positions --league "ENG-Premier League"
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_ROOT))

from backend.db import init_db, upsert_player_positions, _conn
from football_core.percentiles import map_position, POSITION_MAP
from football_core.sources.transfermarkt import _TM_POSITION_TO_BUCKET  # type: ignore[attr-defined]

_TM_CACHE_DIR = _ROOT / ".cache" / "transfermarkt"


# ── TM cache helpers (mirrors transfermarkt.py without importing the heavy requests dep) ──

def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower().strip()


def _safe_filename(s: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", _norm(s))


def _load_tm_cache(player_name: str) -> dict | None:
    path = _TM_CACHE_DIR / f"{_safe_filename(player_name)}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return None


# ── FBref position → structured position ─────────────────────────────────────

def _fbref_to_position(fbref_pos: str) -> dict:
    """Convert a raw FBref position string to {main_position, other_positions, source}."""
    if not fbref_pos.strip():
        return {"main_position": "CM", "other_positions": [], "source": "fbref"}

    # Use map_position on the FULL string so multi-part mappings are respected
    # e.g. "MF,FW" → "W" (winger), "FW,MF" → "CF" (striker), "DF,MF" → "DM"
    main_bucket = map_position(fbref_pos)

    # Derive secondary buckets from individual trailing parts
    parts = [p.strip() for p in fbref_pos.split(",") if p.strip()]
    other_buckets: list[str] = []
    seen = {main_bucket}
    for part in parts[1:]:
        b = POSITION_MAP.get(part)
        if b and b not in seen:
            other_buckets.append(b)
            seen.add(b)

    return {"main_position": main_bucket, "other_positions": other_buckets, "source": "fbref"}


# ── Main enrichment logic ─────────────────────────────────────────────────────

def enrich(league: str | None = None, season: int | None = None) -> None:
    init_db()

    with _conn() as c:
        if league and season:
            player_rows = c.execute(
                "SELECT DISTINCT name, position FROM players WHERE league = ? AND season = ? ORDER BY name",
                (league, season),
            ).fetchall()
        elif league:
            player_rows = c.execute(
                """
                SELECT DISTINCT name, position FROM players
                WHERE league = ?
                ORDER BY name
                """,
                (league,),
            ).fetchall()
        else:
            # All players — take the row with the most minutes per name for the position string
            player_rows = c.execute(
                """
                SELECT name, position FROM players
                WHERE (name, minutes) IN (
                    SELECT name, MAX(minutes) FROM players GROUP BY name
                )
                ORDER BY name
                """,
            ).fetchall()

    total = len(player_rows)
    tm_hits = 0
    fbref_rows: list[dict] = []
    tm_rows: list[dict] = []

    for row in player_rows:
        name: str = row["name"]
        fbref_pos: str = row["position"] or ""

        tm = _load_tm_cache(name)
        if tm and tm.get("main_position"):
            tm_rows.append({
                "name": name,
                "main_position": tm["main_position"],
                "other_positions": tm.get("other_positions") or [],
                "source": "transfermarkt",
            })
            tm_hits += 1
        else:
            entry = _fbref_to_position(fbref_pos)
            entry["name"] = name
            fbref_rows.append(entry)

    upsert_player_positions(tm_rows + fbref_rows)

    print(
        f"Enriched {total} players: "
        f"{tm_hits} from Transfermarkt, {total - tm_hits} from FBref fallback."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate player_positions table")
    parser.add_argument("--league", default=None, help="Restrict to one league (e.g. 'ENG-Premier League')")
    parser.add_argument("--season", type=int, default=None, help="Restrict to one season year (e.g. 2025)")
    args = parser.parse_args()

    enrich(league=args.league, season=args.season)


if __name__ == "__main__":
    main()
