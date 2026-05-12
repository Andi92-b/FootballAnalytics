"""
sources/sofascore.py — Sofascore JSON API (no auth required).

Fetches player season statistics for a given tournament/season.

Fields returned:
  rating, goals, assists, expectedAssists, goalsAssistsSum,
  accuratePasses, totalPasses, accuratePassesPercentage,
  accurateOwnHalfPasses, accurateOppositionHalfPasses, accurateFinalThirdPasses,
  keyPasses, successfulDribbles, successfulDribblesPercentage,
  tackles, interceptions, yellowCards, redCards,
  accurateCrosses, accurateCrossesPercentage,
  totalShots, shotsOnTarget, bigChancesCreated, bigChancesMissed
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

log = logging.getLogger(__name__)

_BASE = "https://api.sofascore.com/api/v1"
_SESSION_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}


def _make_session() -> requests.Session:
    """Create a requests Session with cookies primed from the Sofascore main page."""
    session = requests.Session()
    session.headers.update(_SESSION_HEADERS)
    try:
        # Prime cookies by visiting the main site first
        session.get("https://www.sofascore.com/", timeout=10)
    except Exception:
        pass
    return session


def _cache_path(cache_dir: Path, player_id: int, tournament_id: int, season_id: int) -> Path:
    return cache_dir / "sofascore" / str(player_id) / f"{tournament_id}_{season_id}.json"


def _load_cache(path: Path) -> dict | None:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def fetch_sofascore(
    player_id: int,
    tournament_id: int,
    season_id: int,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict | None:
    """Fetch player stats for one competition-season from Sofascore."""
    path = _cache_path(cache_dir, player_id, tournament_id, season_id)
    if not force_refresh:
        cached = _load_cache(path)
        if cached is not None:
            log.info("Sofascore cache hit: %s", path)
            return cached

    log.info("Sofascore fetching player=%s tournament=%s season=%s", player_id, tournament_id, season_id)
    session = _make_session()
    url = f"{_BASE}/player/{player_id}/unique-tournament/{tournament_id}/season/{season_id}/statistics/overall"
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code != 200:
            log.warning("Sofascore HTTP %s for player %s", resp.status_code, player_id)
            return None
        stats = resp.json().get("statistics")
    except Exception as exc:
        log.warning("Sofascore fetch failed: %s", exc)
        return None

    if stats is None:
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, indent=2))
    log.info("Sofascore cached to %s", path)
    return stats


# ── League-wide stats config ──────────────────────────────────────────────────

# FBref league name → Sofascore unique-tournament ID
SOFASCORE_TOURNAMENT_IDS: dict[str, int] = {
    "GER-Bundesliga":      35,
    "ENG-Premier League":  17,
    "ESP-La Liga":          8,
    "ITA-Serie A":         23,
    "FRA-Ligue 1":         34,
}

# (fbref_league, fbref_season_year) → Sofascore season_id
# fbref_season_year = the year the season starts (e.g. 2025 = 2025/26)
SOFASCORE_SEASON_IDS: dict[tuple[str, int], int] = {
    ("GER-Bundesliga", 2025): 77333,
    ("GER-Bundesliga", 2024): 63516,
    ("GER-Bundesliga", 2023): 52608,
    ("GER-Bundesliga", 2022): 42268,
    ("ENG-Premier League", 2025): 76986,
    ("ENG-Premier League", 2024): 61627,
    ("ENG-Premier League", 2023): 52186,
    ("ENG-Premier League", 2022): 41886,
    ("ESP-La Liga", 2025): 77559,
    ("ESP-La Liga", 2024): 61643,
    ("ESP-La Liga", 2023): 52376,
    ("ITA-Serie A", 2025): 76457,
    ("ITA-Serie A", 2024): 63515,
    ("ITA-Serie A", 2023): 52760,
    ("FRA-Ligue 1", 2025): 77356,
    ("FRA-Ligue 1", 2024): 61736,
    ("FRA-Ligue 1", 2023): 52571,
}

# Stats fields to request from the tournament endpoint — covers all pizza metrics
_LEAGUE_STAT_FIELDS = (
    "tackles,tacklesWon,tacklesWonPercentage,"
    "aerialDuelsWon,aerialDuelsWonPercentage,aerialLost,"
    "successfulDribbles,successfulDribblesPercentage,"
    "ballRecovery,minutesPlayed"
)


def fetch_sofascore_league_stats(
    league: str,
    season: int,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict[str, dict] | None:
    """Fetch stats for all players in a league/season from Sofascore.

    Returns a dict keyed by player name (as Sofascore spells it), e.g.::

        {"Harry Kane": {"tackles": 12, "aerialDuelsWon": 45, ...}, ...}

    Returns None if the league/season is not in our config or the fetch fails.
    """
    tournament_id = SOFASCORE_TOURNAMENT_IDS.get(league)
    season_id = SOFASCORE_SEASON_IDS.get((league, season))
    if tournament_id is None or season_id is None:
        log.debug("No Sofascore config for %s %s — skipping league stats", league, season)
        return None

    path = cache_dir / "sofascore" / f"league_{tournament_id}_{season_id}.json"
    if not force_refresh and path.exists():
        try:
            data = json.loads(path.read_text())
            log.info("Sofascore league stats cache hit: %s (%d players)", path.name, len(data))
            return data
        except Exception:
            pass

    log.info("Fetching Sofascore league stats for %s %s (tournament=%s, season=%s)",
             league, season, tournament_id, season_id)
    session = _make_session()
    url = f"{_BASE}/unique-tournament/{tournament_id}/season/{season_id}/statistics"
    all_players: dict[str, dict] = {}

    try:
        page = 0
        while True:
            params = {
                "limit": 100,
                "order": "-rating",
                "accumulation": "total",
                "fields": _LEAGUE_STAT_FIELDS,
                "offset": page * 100,
            }
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                log.warning("Sofascore league stats HTTP %s (page %d)", resp.status_code, page)
                break
            data = resp.json()
            results = data.get("results", [])
            if not results:
                break
            for entry in results:
                name = entry["player"]["name"]
                pid = entry["player"]["id"]
                stats = {k: v for k, v in entry.items() if k not in ("player", "team")}
                stats["_sofascore_id"] = pid
                all_players[name] = stats
            pages = data.get("pages", 1)
            page += 1
            if page >= pages:
                break
    except Exception as exc:
        log.warning("Sofascore league stats fetch failed: %s", exc)
        if not all_players:
            return None

    if all_players:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(all_players, indent=2))
        log.info("Sofascore league stats cached: %d players → %s", len(all_players), path.name)
    return all_players or None


def fetch_sofascore_seasons(player_id: int, cache_dir: Path, force_refresh: bool = False) -> list[dict]:
    """Return the full competition-season list for a player."""
    path = cache_dir / "sofascore" / str(player_id) / "seasons.json"
    if not force_refresh and path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass

    session = _make_session()
    url = f"{_BASE}/player/{player_id}/statistics/seasons"
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code != 200:
            log.warning("Sofascore seasons HTTP %s", resp.status_code)
            return []
        entries = resp.json().get("uniqueTournamentSeasons", [])
    except Exception as exc:
        log.warning("Sofascore seasons fetch failed: %s", exc)
        return []

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2))
    return entries
