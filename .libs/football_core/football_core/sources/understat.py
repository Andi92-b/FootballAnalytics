"""
sources/understat.py — Tier B: xG and xA via Understat's JSON API.

Coverage: Big-5 leagues only (EPL, La Liga, Bundesliga, Serie A, Ligue 1).
Returns None for any league not in the coverage map (e.g. World Cup).

Fields returned per player (keyed by normalised player name):
  { "npxG": float, "xA": float, "xG": float, "shots": int }
"""

from __future__ import annotations

import asyncio
import json
import logging
import unicodedata
from pathlib import Path

import aiohttp

log = logging.getLogger(__name__)

# Understat league slug → soccerdata league ID
UNDERSTAT_LEAGUE_MAP: dict[str, str] = {
    "ENG-Premier League": "EPL",
    "ESP-La Liga": "La_liga",
    "GER-Bundesliga": "Bundesliga",
    "ITA-Serie A": "Serie_A",
    "FRA-Ligue 1": "Ligue_1",
}

_BASE = "https://understat.com"


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower().strip()


def _cache_path(cache_dir: Path, league: str, season: int) -> Path:
    slug = UNDERSTAT_LEAGUE_MAP.get(league, "")
    return cache_dir / "understat" / slug / f"{season}.json"


def _load_cache(path: Path) -> dict | None:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def _save_cache(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


async def _fetch_async(league_slug: str, season: int) -> list[dict]:
    url = f"{_BASE}/getLeagueData/{league_slug}/{season}"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"},
        ) as r:
            r.raise_for_status()
            data = await r.json(content_type=None)
    return data.get("players", [])


def fetch_understat(
    league: str,
    season: int,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict[str, dict] | None:
    """
    Fetch xG / xA data from Understat for the given league and season.

    Returns a dict keyed by normalised player name:
      { "virgil van dijk": {"npxG": 2.82, "xA": 1.21, "xG": 2.82, "shots": 26}, ... }

    Returns None if the league is not in Understat's coverage.
    """
    league_slug = UNDERSTAT_LEAGUE_MAP.get(league)
    if league_slug is None:
        log.info("Understat: league %r not in coverage — skipping", league)
        return None

    path = _cache_path(cache_dir, league, season)
    if not force_refresh:
        cached = _load_cache(path)
        if cached is not None:
            log.info("Understat cache hit: %s", path)
            return cached

    log.info("Fetching Understat data for %s %s …", league, season)
    try:
        import concurrent.futures
        # asyncio.run() raises RuntimeError if called from a running event loop
        # (e.g. inside FastAPI). Run in a thread instead — threads always have
        # a fresh event loop available.
        def _run():
            import asyncio as _asyncio
            return _asyncio.run(_fetch_async(league_slug, season))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            players_raw = pool.submit(_run).result(timeout=30)
    except Exception as exc:
        log.warning("Understat fetch failed: %s", exc)
        return None

    result: dict[str, dict] = {}
    for p in players_raw:
        name = p.get("player_name", "")
        key = _normalize(name)
        result[key] = {
            "npxG": float(p.get("npxG", 0) or 0),
            "xA": float(p.get("xA", 0) or 0),
            "xG": float(p.get("xG", 0) or 0),
            "shots": int(p.get("shots", 0) or 0),
            "player_name": name,
        }

    _save_cache(result, path)
    log.info("Understat: fetched %d players", len(result))
    return result
