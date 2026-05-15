"""
db.py — SQLite player index + pizza-data cache.

Tables
------
players(id, name, team, league, position, season, minutes)
    Player index for autocomplete search and non-registry fallback.
    `position` is the raw FBref position string (e.g. "FW,MF", "DF").

player_positions(id, name, main_position, other_positions, source, updated_at)
    Canonical position data — one row per player name.
    `main_position`   : TM granular label when available ("Left Winger"),
                        else FBref position bucket ("W", "CF", "CB", …).
    `other_positions` : JSON array of additional positions in the same format.
    `source`          : "transfermarkt" | "fbref"
    Updated on every live TM fetch and by the enrich_positions script.

player_cache(id, name, league, season, matches_played, cached_until, pizza_json)
    Computed PizzaData keyed on (name, league, season).
    - matches_played  : MP from FBref standard table at compute time (staleness signal)
    - cached_until    : ISO-8601 UTC datetime; serve from cache while before this time
    - pizza_json      : full PizzaData serialised as JSON
"""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / ".cache" / "players.db"

# Cache TTL for in-season data (weeks with new matches).
# After this window the MP check determines whether to recompute.
_CACHE_TTL_DAYS = 3


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    """Create all tables if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT NOT NULL,
                team     TEXT,
                league   TEXT NOT NULL,
                position TEXT,
                season   INTEGER NOT NULL,
                minutes  INTEGER DEFAULT 0,
                UNIQUE(name, league, season)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_players_name ON players(name)")

        c.execute("""
            CREATE TABLE IF NOT EXISTS player_positions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL UNIQUE,
                main_position   TEXT NOT NULL,
                other_positions TEXT NOT NULL DEFAULT '[]',
                source          TEXT NOT NULL DEFAULT 'fbref',
                updated_at      TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_player_positions_name ON player_positions(name)")

        c.execute("""
            CREATE TABLE IF NOT EXISTS player_cache (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL,
                league         TEXT NOT NULL,
                season         INTEGER NOT NULL,
                matches_played INTEGER NOT NULL DEFAULT 0,
                cached_until   TEXT NOT NULL,
                pizza_json     TEXT NOT NULL,
                UNIQUE(name, league, season)
            )
        """)


def upsert_players(rows: list[dict]) -> None:
    """Insert or replace player rows. Each dict must have: name, team, league, position, season, minutes."""
    with _conn() as c:
        c.executemany(
            """
            INSERT INTO players (name, team, league, position, season, minutes)
            VALUES (:name, :team, :league, :position, :season, :minutes)
            ON CONFLICT(name, league, season) DO UPDATE SET
                team     = excluded.team,
                position = excluded.position,
                minutes  = excluded.minutes
            """,
            rows,
        )


# ── Player positions ──────────────────────────────────────────────────────────

def upsert_player_positions(rows: list[dict]) -> None:
    """Insert or update canonical position data.

    Each dict must have: name, main_position, other_positions (list[str]), source.
    """
    now = datetime.now(tz=timezone.utc).isoformat()
    with _conn() as c:
        c.executemany(
            """
            INSERT INTO player_positions (name, main_position, other_positions, source, updated_at)
            VALUES (:name, :main_position, :other_positions, :source, :updated_at)
            ON CONFLICT(name) DO UPDATE SET
                main_position   = excluded.main_position,
                other_positions = excluded.other_positions,
                source          = excluded.source,
                updated_at      = excluded.updated_at
            """,
            [
                {
                    "name": r["name"],
                    "main_position": r["main_position"],
                    "other_positions": json.dumps(r.get("other_positions", [])),
                    "source": r.get("source", "fbref"),
                    "updated_at": now,
                }
                for r in rows
            ],
        )


def get_position(name: str) -> dict | None:
    """Return canonical position data for a player, or None if not in the table.

    Returns: {name, main_position, other_positions: list[str], source}
    """
    with _conn() as c:
        row = c.execute(
            "SELECT name, main_position, other_positions, source FROM player_positions WHERE name = ?",
            (name,),
        ).fetchone()
        if not row:
            return None
    return {
        "name": row["name"],
        "main_position": row["main_position"],
        "other_positions": json.loads(row["other_positions"]),
        "source": row["source"],
    }


def get_positions_for_league(league: str, season: int) -> dict[str, dict]:
    """Return a {player_name: position_data} mapping for all players.

    Only includes players present in the player_positions table.
    Used to pre-load positions before calling compute_percentiles.
    """
    with _conn() as c:
        rows = c.execute(
            """
            SELECT name, main_position, other_positions, source
            FROM player_positions
            """,
        ).fetchall()
    result: dict[str, dict] = {}
    for row in rows:
        result[row["name"]] = {
            "main_position": row["main_position"],
            "other_positions": json.loads(row["other_positions"]),
            "source": row["source"],
        }
    return result


def search_players(query: str, limit: int = 10) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """
            SELECT name, team, league, position, season, minutes
            FROM players
            WHERE name LIKE ?
            ORDER BY minutes DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_player_entry(name: str) -> dict | None:
    """Return the most-played season entry for a player (exact name match, then case-insensitive)."""
    with _conn() as c:
        row = c.execute(
            "SELECT name, team, league, position, season, minutes FROM players WHERE name = ? ORDER BY minutes DESC LIMIT 1",
            (name,),
        ).fetchone()
        if not row:
            row = c.execute(
                "SELECT name, team, league, position, season, minutes FROM players WHERE name LIKE ? ORDER BY minutes DESC LIMIT 1",
                (name,),
            ).fetchone()
    return dict(row) if row else None


def get_player_seasons(name: str) -> list[dict]:
    """Return all seasons (ordered by season asc) for a player."""
    with _conn() as c:
        rows = c.execute(
            "SELECT name, team, league, position, season, minutes FROM players WHERE name = ? ORDER BY season ASC",
            (name,),
        ).fetchall()
        if not rows:
            rows = c.execute(
                "SELECT name, team, league, position, season, minutes FROM players WHERE name LIKE ? ORDER BY season ASC",
                (name,),
            ).fetchall()
    return [dict(r) for r in rows]


# ── Pizza-data cache ──────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def cache_get(name: str, league: str, season: int, current_mp: int) -> dict | None:
    """
    Return cached pizza JSON if the cache is still valid.

    Cache is valid when BOTH conditions hold:
      1. cached_until has not passed (TTL not expired)
      2. matches_played matches current_mp (no new match data)

    Returns the deserialised pizza dict, or None if stale/missing.
    """
    with _conn() as c:
        row = c.execute(
            "SELECT matches_played, cached_until, pizza_json FROM player_cache WHERE name=? AND league=? AND season=?",
            (name, league, season),
        ).fetchone()
    if not row:
        return None
    cached_until = datetime.fromisoformat(row["cached_until"])
    if _now_utc() > cached_until:
        return None  # TTL expired — check for fresh data
    if row["matches_played"] != current_mp:
        return None  # New match played — recompute
    return json.loads(row["pizza_json"])


def cache_set(name: str, league: str, season: int, matches_played: int, pizza_data: dict) -> None:
    """
    Write pizza data to the cache with a fresh TTL.

    `pizza_data` should be a dict produced by `PizzaData.model_dump()`.
    """
    cached_until = (_now_utc() + timedelta(days=_CACHE_TTL_DAYS)).isoformat()
    with _conn() as c:
        c.execute(
            """
            INSERT INTO player_cache (name, league, season, matches_played, cached_until, pizza_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name, league, season) DO UPDATE SET
                matches_played = excluded.matches_played,
                cached_until   = excluded.cached_until,
                pizza_json     = excluded.pizza_json
            """,
            (name, league, season, matches_played, cached_until, json.dumps(pizza_data)),
        )


def cache_invalidate(name: str, league: str, season: int) -> None:
    """Force-expire a cache entry (e.g. after a manual data refresh)."""
    with _conn() as c:
        c.execute(
            "DELETE FROM player_cache WHERE name=? AND league=? AND season=?",
            (name, league, season),
        )
