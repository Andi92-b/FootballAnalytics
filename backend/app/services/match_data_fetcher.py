"""
Multi-source Bayern match data fetcher.

Priority / coverage:
  1. Understat team endpoint  — Bundesliga xG + results (httpx; works from any IP)
  2. FBref read_schedule()    — Bundesliga + CL schedule with match xG (requires soccerdata)
  3. FBref read_shots()       — shot coordinates per Bundesliga match (requires soccerdata; slow)

Both FBref paths degrade gracefully: if soccerdata / pandas are unavailable (e.g. cloud
containers), only the Understat path runs and soccerdata paths log a warning and return [].

Usage:
    from backend.app.services.match_data_fetcher import fetch_and_store
    result = fetch_and_store(season=2025, cache_dir=Path(".cache"))
"""
from __future__ import annotations

import html as html_mod
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from backend import db
from backend.app.services.match_catalogue import _slug

log = logging.getLogger(__name__)

UNDERSTAT_TEAM_SLUG = "Bayern_Munich"
BUNDESLIGA_LABEL = "Bundesliga"
CL_LABEL = "Champions League"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_path_understat(cache_dir: Path, season: int) -> Path:
    return cache_dir / "understat" / "Bayern_Munich" / f"{season}_matches.json"


def _cache_path_fbref_schedule(cache_dir: Path, league: str, season: int) -> Path:
    safe = league.replace(" ", "_").replace("-", "_")
    return cache_dir / "fbref" / safe / str(season) / "schedule.json"


def _load_json_cache(path: Path) -> list[dict] | None:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def _save_json_cache(data: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, default=str))


# ── Understat team endpoint ───────────────────────────────────────────────────

def fetch_understat_matches(
    season: int,
    cache_dir: Path,
    force_refresh: bool = False,
) -> list[dict]:
    """
    Fetch all Bayern Bundesliga matches from Understat for the given season.

    Returns list of match dicts with keys:
        id, date, competition, home_team, away_team,
        home_goals, away_goals, home_xg, away_xg

    Only matches where isResult=true (already played) are returned.
    Future fixtures that are in the page but have no score are skipped.
    """
    cache_path = _cache_path_understat(cache_dir, season)
    if not force_refresh:
        cached = _load_json_cache(cache_path)
        if cached is not None:
            log.info("Understat team cache hit: %s", cache_path)
            return cached

    url = f"https://understat.com/team/{UNDERSTAT_TEAM_SLUG}/{season}"
    log.info("Fetching Understat team page for season %s…", season)
    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=20.0) as client:
        resp = client.get(url)
        resp.raise_for_status()

    matches = _parse_understat_page(resp.text)
    _save_json_cache(matches, cache_path)
    log.info("Understat team: parsed %d played matches", len(matches))
    return matches


def _parse_understat_page(page_text: str) -> list[dict]:
    pattern = re.search(
        r"var\s+datesData\s*=\s*JSON\.parse\('(.*?)'\)",
        page_text,
        re.DOTALL,
    )
    if not pattern:
        log.warning("Understat: datesData not found in page")
        return []

    raw = html_mod.unescape(pattern.group(1))
    try:
        entries: list[dict] = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("Understat: JSON parse failed: %s", exc)
        return []

    matches: list[dict] = []
    for entry in entries:
        if not entry.get("isResult"):
            continue

        date_str = entry.get("datetime", "")
        try:
            iso_date = datetime.strptime(date_str[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            continue

        h = entry.get("h", {})
        a = entry.get("a", {})
        goals = entry.get("goals", {})
        xg = entry.get("xG", {})

        home_team = h.get("title", "")
        away_team = a.get("title", "")

        try:
            home_goals: int | None = int(goals.get("h", ""))
            away_goals: int | None = int(goals.get("a", ""))
        except (ValueError, TypeError):
            home_goals = away_goals = None

        try:
            home_xg: float | None = float(xg.get("h", ""))
            away_xg: float | None = float(xg.get("a", ""))
        except (ValueError, TypeError):
            home_xg = away_xg = None

        if not home_team or not away_team:
            continue

        match_id = _slug(iso_date, home_team, away_team)
        matches.append({
            "id": match_id,
            "date": iso_date,
            "competition": BUNDESLIGA_LABEL,
            "home_team": home_team,
            "away_team": away_team,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "home_xg": home_xg,
            "away_xg": away_xg,
        })

    return matches


# ── FBref schedule (soccerdata) ───────────────────────────────────────────────

def fetch_fbref_schedule(
    league: str,
    season: int,
    cache_dir: Path,
    force_refresh: bool = False,
) -> list[dict]:
    """
    Fetch match schedule from FBref via soccerdata.read_schedule().

    Returns list of match dicts. Returns [] if soccerdata is unavailable.
    """
    try:
        import soccerdata as sd  # type: ignore
        import pandas as pd  # type: ignore
    except ImportError:
        log.info("soccerdata/pandas not installed — skipping FBref schedule for %s", league)
        return []

    cache_path = _cache_path_fbref_schedule(cache_dir, league, season)
    if not force_refresh:
        cached = _load_json_cache(cache_path)
        if cached is not None:
            log.info("FBref schedule cache hit: %s", cache_path)
            return cached

    log.info("Fetching FBref schedule for %s %s…", league, season)
    try:
        fbref = sd.FBref(leagues=league, seasons=season)
        df = fbref.read_schedule()
        df = df.reset_index()

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["_".join(str(c) for c in col if c).strip("_") for col in df.columns]

        matches = _normalize_fbref_schedule(df)
        _save_json_cache(matches, cache_path)
        log.info("FBref schedule: %d matches for %s %s", len(matches), league, season)
        time.sleep(4)
        return matches
    except Exception as exc:
        log.warning("FBref schedule fetch failed for %s/%s: %s", league, season, exc)
        return []


def _normalize_fbref_schedule(df: Any) -> list[dict]:
    """Convert FBref schedule DataFrame rows into match dicts."""
    import pandas as pd  # type: ignore

    matches: list[dict] = []
    cols = list(df.columns)

    def _find_col(*candidates: str) -> str | None:
        for c in candidates:
            if c in cols:
                return c
        # Partial match fallback
        for cand in candidates:
            for c in cols:
                if cand.lower() in c.lower():
                    return c
        return None

    date_col = _find_col("date", "Date")
    home_col = _find_col("home", "Home", "home_team")
    away_col = _find_col("away", "Away", "away_team")
    score_col = _find_col("score", "Score", "result")
    home_xg_col = _find_col("home_xg", "xg", "xG", "xg_home")
    away_xg_col = _find_col("away_xg", "xg_away", "xG_away")

    if not all([date_col, home_col, away_col]):
        log.warning("FBref schedule: required columns not found in %s", cols[:20])
        return []

    for _, row in df.iterrows():
        date_val = row.get(date_col)
        if pd.isna(date_val) if hasattr(pd, "isna") else not date_val:
            continue

        try:
            if hasattr(date_val, "strftime"):
                iso_date = date_val.strftime("%Y-%m-%d")
            else:
                iso_date = str(date_val)[:10]
        except Exception:
            continue

        home_team = str(row.get(home_col, "")).strip()
        away_team = str(row.get(away_col, "")).strip()
        if not home_team or not away_team or home_team == "nan" or away_team == "nan":
            continue

        home_goals: int | None = None
        away_goals: int | None = None
        if score_col:
            score_text = str(row.get(score_col, ""))
            m = re.search(r"(\d+)[–\-](\d+)", score_text)
            if m:
                home_goals, away_goals = int(m.group(1)), int(m.group(2))

        home_xg: float | None = None
        away_xg: float | None = None
        if home_xg_col:
            try:
                v = float(row.get(home_xg_col, "nan"))
                home_xg = None if v != v else v  # NaN check
            except (ValueError, TypeError):
                pass
        if away_xg_col:
            try:
                v = float(row.get(away_xg_col, "nan"))
                away_xg = None if v != v else v
            except (ValueError, TypeError):
                pass

        match_id = _slug(iso_date, home_team, away_team)
        matches.append({
            "id": match_id,
            "date": iso_date,
            "competition": BUNDESLIGA_LABEL,
            "home_team": home_team,
            "away_team": away_team,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "home_xg": home_xg,
            "away_xg": away_xg,
        })

    return matches


# ── FBref shots (soccerdata) ──────────────────────────────────────────────────

def fetch_fbref_shots(
    league: str,
    season: int,
    cache_dir: Path,
    team_filter: str = "Bayern München",
    force_refresh: bool = False,
) -> list[dict]:
    """
    Fetch shot-by-shot data for Bayern from FBref via soccerdata.read_shots().

    This is slow (scrapes individual match pages) — only call when needed.
    Returns [] if soccerdata is unavailable or on error.
    """
    try:
        import soccerdata as sd  # type: ignore
        import pandas as pd  # type: ignore
    except ImportError:
        log.info("soccerdata/pandas not installed — skipping FBref shots for %s", league)
        return []

    cache_path = cache_dir / "fbref" / league.replace(" ", "_") / str(season) / "shots.json"
    if not force_refresh:
        cached = _load_json_cache(cache_path)
        if cached is not None:
            log.info("FBref shots cache hit: %s", cache_path)
            return cached

    log.info("Fetching FBref shots for %s %s (slow)…", league, season)
    try:
        fbref = sd.FBref(leagues=league, seasons=season)
        df = fbref.read_shots()
        df = df.reset_index()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["_".join(str(c) for c in col if c).strip("_") for col in df.columns]

        shots = _normalize_fbref_shots(df, team_filter=team_filter)
        _save_json_cache(shots, cache_path)
        log.info("FBref shots: %d shots for %s", len(shots), team_filter)
        return shots
    except Exception as exc:
        log.warning("FBref shots fetch failed: %s", exc)
        return []


def _normalize_fbref_shots(df: Any, team_filter: str) -> list[dict]:
    import pandas as pd  # type: ignore

    shots: list[dict] = []
    cols = list(df.columns)

    def _find_col(*candidates: str) -> str | None:
        for c in candidates:
            if c in cols:
                return c
        for cand in candidates:
            for c in cols:
                if cand.lower() in c.lower():
                    return c
        return None

    team_col = _find_col("team", "squad", "Team")
    date_col = _find_col("date", "Date")
    home_col = _find_col("home", "Home")
    away_col = _find_col("away", "Away")
    player_col = _find_col("player", "Player")
    minute_col = _find_col("minute", "Minute", "min")
    xg_col = _find_col("xg", "xG", "xGoal")
    result_col = _find_col("outcome", "result", "Result", "Outcome")
    situation_col = _find_col("situation", "Situation")
    body_col = _find_col("body_part", "BodyPart", "body")
    x_col = _find_col("x", "X", "shot_x")
    y_col = _find_col("y", "Y", "shot_y")

    for _, row in df.iterrows():
        team = str(row.get(team_col, "")) if team_col else ""
        if team_filter.lower() not in team.lower():
            continue

        date_val = row.get(date_col) if date_col else None
        if date_val is None or (hasattr(pd, "isna") and pd.isna(date_val)):
            continue

        try:
            if hasattr(date_val, "strftime"):
                iso_date = date_val.strftime("%Y-%m-%d")
            else:
                iso_date = str(date_val)[:10]
        except Exception:
            continue

        home_team = str(row.get(home_col, "")).strip() if home_col else ""
        away_team = str(row.get(away_col, "")).strip() if away_col else ""
        match_id = _slug(iso_date, home_team, away_team) if home_team and away_team else ""

        def _safe_float(key: str | None) -> float | None:
            if not key:
                return None
            try:
                v = float(row.get(key, "nan"))
                return None if v != v else v
            except (ValueError, TypeError):
                return None

        def _safe_int(key: str | None) -> int | None:
            if not key:
                return None
            try:
                return int(row.get(key, 0))
            except (ValueError, TypeError):
                return None

        shots.append({
            "match_id": match_id,
            "x": _safe_float(x_col),
            "y": _safe_float(y_col),
            "xG": _safe_float(xg_col),
            "result": str(row.get(result_col, "")).strip() if result_col else None,
            "situation": str(row.get(situation_col, "")).strip() if situation_col else None,
            "shot_type": str(row.get(body_col, "")).strip() if body_col else None,
            "minute": _safe_int(minute_col),
            "player": str(row.get(player_col, "")).strip() if player_col else None,
            "team": team,
        })

    return shots


# ── Merge helpers ─────────────────────────────────────────────────────────────

def _merge_matches(
    understat: list[dict],
    fbref: list[dict],
) -> list[dict]:
    """
    Merge Understat and FBref match lists, deduplicated by id.

    FBref data fills gaps not covered by Understat (e.g. CL).
    When both have the same match, Understat xG values are preferred
    (they're generally more up-to-date for Bundesliga).
    """
    by_id: dict[str, dict] = {}

    # FBref first (lower priority)
    for m in fbref:
        by_id[m["id"]] = m

    # Understat second (wins on conflict for Bundesliga)
    for m in understat:
        if m["id"] in by_id:
            existing = by_id[m["id"]]
            # Prefer Understat xG when available
            if m.get("home_xg") is not None:
                existing["home_xg"] = m["home_xg"]
                existing["away_xg"] = m["away_xg"]
            if m.get("home_goals") is not None:
                existing["home_goals"] = m["home_goals"]
                existing["away_goals"] = m["away_goals"]
        else:
            by_id[m["id"]] = m

    return list(by_id.values())


# ── Main entry point ──────────────────────────────────────────────────────────

def fetch_and_store(
    season: int = 2025,
    cache_dir: Path | None = None,
    force_refresh: bool = False,
    include_shots: bool = False,
) -> dict:
    """
    Fetch Bayern match data from all available sources and upsert into the DB.

    Args:
        season:         Starting year of the season (2025 = 2025-26).
        cache_dir:      Override cache directory (defaults to .cache/).
        force_refresh:  Bypass all caches and re-fetch.
        include_shots:  Also fetch FBref shot coordinates (slow, requires soccerdata).

    Returns:
        {"upserted": N, "sources": [...]}
    """
    if cache_dir is None:
        cache_dir = Path(__file__).parents[4] / ".cache"

    sources_used: list[str] = []

    # 1. Understat team data (Bundesliga, works from any IP)
    understat_matches: list[dict] = []
    try:
        understat_matches = fetch_understat_matches(season, cache_dir, force_refresh=force_refresh)
        if understat_matches:
            sources_used.append("understat")
    except Exception as exc:
        log.warning("Understat team fetch failed: %s", exc)

    # 2. FBref schedule — Bundesliga (adds CL data and xG cross-reference)
    fbref_bl: list[dict] = []
    fbref_cl: list[dict] = []
    try:
        fbref_bl = fetch_fbref_schedule("GER-Bundesliga", season, cache_dir, force_refresh=force_refresh)
        if fbref_bl:
            sources_used.append("fbref_bundesliga")
    except Exception as exc:
        log.warning("FBref Bundesliga schedule fetch failed: %s", exc)

    try:
        fbref_cl = fetch_fbref_schedule("Champions League", season, cache_dir, force_refresh=force_refresh)
        for m in fbref_cl:
            m["competition"] = CL_LABEL
        if fbref_cl:
            sources_used.append("fbref_champions_league")
    except Exception as exc:
        log.warning("FBref CL schedule fetch failed: %s", exc)

    # Merge Understat + FBref
    bundesliga_merged = _merge_matches(understat_matches, fbref_bl)
    all_matches = bundesliga_merged + fbref_cl

    # 3. Upsert matches
    for m in all_matches:
        db.upsert_match(m)

    # 4. FBref shots (optional, slow)
    shots_stored = 0
    if include_shots:
        try:
            shots = fetch_fbref_shots("GER-Bundesliga", season, cache_dir, force_refresh=force_refresh)
            valid_shots = [s for s in shots if s.get("match_id")]
            if valid_shots:
                db.insert_match_shots(valid_shots)
                shots_stored = len(valid_shots)
                sources_used.append("fbref_shots")
        except Exception as exc:
            log.warning("FBref shots storage failed: %s", exc)

    return {
        "upserted": len(all_matches),
        "shots_stored": shots_stored,
        "sources": sources_used,
    }
