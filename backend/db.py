"""
db.py — SQLite player index.

Schema:
    players(id, name, team, league, position, season, minutes)

Used for:
  - autocomplete search (GET /api/players/search?q=...)
  - league/season fallback for players not in player_registry.json
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / ".cache" / "players.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    """Create the players table if it doesn't exist."""
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


def search_players(query: str, limit: int = 10) -> list[dict]:
    """Return players whose name contains `query` (case-insensitive), ordered by minutes desc."""
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
