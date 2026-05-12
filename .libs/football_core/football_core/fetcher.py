"""
fetcher.py — soccerdata scrape + JSON cache read/write.
"""

import time
import logging
from pathlib import Path

import pandas as pd
import soccerdata as sd
from soccerdata.fbref import FBREF_API, _parse_table
from lxml import html as lhtml

log = logging.getLogger(__name__)

# Tables natively supported by soccerdata read_player_season_stats
SD_TABLES = ["standard", "shooting", "misc"]

# Tables fetched via soccerdata's internal HTTP layer (not in built-in list)
EXTRA_TABLES = ["passing", "passing_types", "defense", "possession"]

ALL_TABLES = SD_TABLES + EXTRA_TABLES

# Stat type → URL page segment
_PAGE = {
    "standard": "stats",
    "standard": "stats",
    "shooting": "shooting",
    "misc": "misc",
    "passing": "passing",
    "passing_types": "passing_types",
    "defense": "defense",
    "possession": "possession",
}


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _cache_path(cache_dir: Path, league: str, season: int, table: str) -> Path:
    safe_league = league.replace(" ", "_").replace("-", "_")
    return cache_dir / safe_league / str(season) / f"{table}.json"


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = ["_".join(str(c) for c in col).strip("_") for col in df.columns]
    # Simplify "Unnamed: N_level_0_ColumnName" → "ColumnName"
    import re
    new_cols = []
    for col in df.columns:
        m = re.match(r'^Unnamed: \d+_level_0_(.+)$', str(col))
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


# ── Extra-table fetcher ────────────────────────────────────────────────────────

def _fetch_extra_table(
    fbref: sd.FBref,
    stat_type: str,
    season_url: str,
    lkey: str,
    skey: str,
) -> pd.DataFrame | None:
    """Fetch a stat table not in soccerdata's built-in list via its internal HTTP layer."""
    page = _PAGE[stat_type]
    parts = season_url.split("/")
    url = FBREF_API + "/".join(parts[:-1]) + f"/{page}/" + parts[-1]
    filepath = fbref.data_dir / f"players_{lkey}_{skey}_{stat_type}.html"

    log.info("Fetching extra table %s from %s", stat_type, url)
    reader = fbref.get(url, filepath)
    tree = lhtml.parse(reader)

    # FBref embeds the player stats table inside an HTML comment — mirror soccerdata's approach
    comments = tree.xpath(f"//comment()[contains(.,'div_stats_{stat_type}')]")
    if not comments:
        log.warning("No comment block found for stats_%s", stat_type)
        return None

    # Use lxml.html.fromstring so _parse_table receives the correct element type
    inner = lhtml.fromstring(comments[0].text)
    html_tables = inner.xpath(f"//table[contains(@id, 'stats_{stat_type}')]")
    if not html_tables:
        log.warning("No table containing stats_%s found in comment block", stat_type)
        return None

    df = _parse_table(html_tables[0])
    return _flatten_columns(df)


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_tables(
    league: str,
    season: int,
    cache_dir: Path,
    tables: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch (or load from cache) each stat table for the given league/season."""
    if tables is None:
        tables = ALL_TABLES

    fbref = sd.FBref(leagues=league, seasons=season)

    # Resolve season URL once (needed for extra-table fetching)
    seasons_df = fbref.read_seasons()
    season_url = lkey_found = skey_found = None
    for (lkey, skey), season_row in seasons_df.iterrows():
        season_url = season_row.url
        lkey_found, skey_found = lkey, skey
        break

    result: dict[str, pd.DataFrame] = {}

    for table in tables:
        path = _cache_path(cache_dir, league, season, table)
        cached = _load_cache(path)
        if cached is not None:
            log.info("Cache hit: %s", path)
            result[table] = cached
            continue

        log.info("Scraping %s …", table)
        if table in SD_TABLES:
            df = fbref.read_player_season_stats(stat_type=table)
            df = df.reset_index()
            df = _flatten_columns(df)
        else:
            if season_url is None:
                log.warning("No season URL — skipping extra table %s", table)
                continue
            df = _fetch_extra_table(fbref, table, season_url, lkey_found, skey_found)
            if df is None:
                continue

        _save_cache(df, path)
        result[table] = df
        time.sleep(4)

    return result


def _normalize(s: str) -> str:
    """Lowercase + strip accents for accent-insensitive matching."""
    import unicodedata
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


def get_player_row(df: pd.DataFrame, player_name: str) -> pd.Series | None:
    """Return the player's row with the most minutes (handles mid-season transfers)."""
    # Find the player name column — handles 'player', 'Player', or 'Unnamed: 1_level_0_Player'
    player_col = next(
        (c for c in df.columns if str(c).lower() == "player" or str(c).endswith("_Player")),
        None,
    )
    if player_col is None:
        try:
            df = df.reset_index()
            player_col = next(
                (c for c in df.columns if str(c).lower() == "player" or str(c).endswith("_Player")),
                None,
            )
        except Exception:
            pass
    if player_col is None:
        return None

    # Exact match first; fall back to accent-insensitive match
    rows = df[df[player_col] == player_name]
    if rows.empty:
        norm_query = _normalize(player_name)
        mask = df[player_col].apply(lambda n: _normalize(str(n)) == norm_query)
        rows = df[mask]
    if rows.empty:
        return None
    if len(rows) == 1:
        return rows.iloc[0]

    for min_col in ["Playing Time_Min", "Min", "Playing_Time_Min", "MP"]:
        if min_col in rows.columns:
            cleaned = rows[min_col].astype(str).str.replace(",", "").astype(float)
            return rows.loc[cleaned.idxmax()]
    return rows.iloc[0]


def merge_player_stats(player_name: str, tables: dict[str, pd.DataFrame]) -> dict:
    """Merge per-table player rows into a flat dict keyed by '<table>.<column>'."""
    merged: dict = {}
    for table_name, df in tables.items():
        row = get_player_row(df, player_name)
        if row is not None:
            for col, val in row.items():
                merged[f"{table_name}.{col}"] = val
    return merged


def add_team_poss(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Compute team possession % from standard table and merge it back in."""
    standard = tables.get("standard")
    if standard is None:
        return tables

    standard = _flatten_columns(standard)
    poss_col = next((c for c in standard.columns if c.lower() in ("poss", "possession")), None)
    squad_col = next((c for c in standard.columns if c.lower() == "squad"), None)

    if poss_col and squad_col:
        team_poss = (
            standard.groupby(squad_col)[poss_col]
            .mean()
            .div(100)
            .rename("team_poss")
            .reset_index()
        )
        standard = standard.merge(team_poss, on=squad_col, how="left")
        tables = dict(tables)
        tables["standard"] = standard

    return tables
