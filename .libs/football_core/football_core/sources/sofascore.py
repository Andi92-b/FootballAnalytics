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
