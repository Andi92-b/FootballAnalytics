"""
sources/footystats.py — FootyStats HTML scraper.

Scrapes the player stats page at footystats.org to retrieve:
- Current season: goals, assists, xG, xA, shots, SoT, passes, pass%, key passes,
  dribbles, tackles, interceptions, aerial duels won, ground duels won, fouls, cards
- Previous seasons summary table (goals, assists, minutes, cards per competition)

Cache: .cache/footystats/{slug_normalized}.json
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

_BASE = "https://footystats.org/players"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}


def _cache_path(cache_dir: Path, slug: str) -> Path:
    safe = slug.replace("/", "_").replace(" ", "_")
    return cache_dir / "footystats" / f"{safe}.json"


def _parse_number(text: str) -> float | None:
    """Parse a number string like '16.44' or '1,244' → float."""
    cleaned = text.strip().replace(",", "").replace("%", "")
    if not cleaned or cleaned in ("-", "N/A", "n/a", ""):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _scrape(slug: str) -> dict:
    url = f"{_BASE}/{slug}"
    log.info("FootyStats scraping %s", url)
    resp = requests.get(url, headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    result: dict = {"url": url, "slug": slug, "current_season": {}, "previous_seasons": []}

    # --- Current season stats tables ---
    # FootyStats uses <table> elements with stat labels in <th> or stat rows with class patterns
    # Primary approach: find all <tr> rows inside stat tables and build key-value pairs
    stat_map: dict[str, float] = {}

    # Look for all tables on the page and extract label-value pairs
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True)
                value_text = cells[1].get_text(strip=True)
                val = _parse_number(value_text)
                if label and val is not None:
                    # Map to canonical keys
                    key = _canonicalize(label)
                    if key:
                        stat_map[key] = val

    # Fallback: also grab stat items from div-based layouts (footystats uses both)
    for item in soup.find_all(class_=re.compile(r"stat|metric", re.I)):
        children = item.find_all(recursive=False)
        if len(children) >= 2:
            label = children[0].get_text(strip=True)
            value_text = children[1].get_text(strip=True)
            val = _parse_number(value_text)
            if label and val is not None:
                key = _canonicalize(label)
                if key:
                    stat_map.setdefault(key, val)

    result["current_season"] = stat_map

    # --- Previous seasons table ---
    seasons = []
    # Find the "Previous Seasons" section
    for section_header in soup.find_all(["h2", "h3", "h4", "h5"]):
        if "previous" in section_header.get_text(strip=True).lower():
            # Season entries follow as h5 + table
            sibling = section_header.find_next_sibling()
            while sibling:
                if sibling.name in ["h2", "h3"] and "previous" not in sibling.get_text(strip=True).lower():
                    break
                if sibling.name in ["h4", "h5"]:
                    season_label = sibling.get_text(strip=True)
                    # Find next table
                    tbl = sibling.find_next("table")
                    if tbl:
                        season_entry = {"season": season_label, "competitions": []}
                        for row in tbl.find_all("tr"):
                            cells = row.find_all("td")
                            if len(cells) >= 5:
                                comp_link = cells[0].find("a")
                                competition = comp_link.get_text(strip=True) if comp_link else cells[0].get_text(strip=True)
                                # columns: competition, MP, goals, assists, cards, minutes (roughly)
                                entry = {
                                    "competition": competition,
                                    "matches": _parse_number(cells[1].get_text(strip=True)),
                                    "goals": _parse_number(cells[2].get_text(strip=True)),
                                    "assists": _parse_number(cells[3].get_text(strip=True)),
                                }
                                if any(v is not None for v in entry.values()):
                                    season_entry["competitions"].append(entry)
                        if season_entry["competitions"]:
                            seasons.append(season_entry)
                sibling = sibling.find_next_sibling()
            break

    result["previous_seasons"] = seasons

    # --- Player metadata (name, position, team) ---
    meta: dict[str, str] = {}
    name_el = soup.find("h1")
    if name_el:
        meta["name"] = name_el.get_text(strip=True).replace("Stats", "").strip()

    for el in soup.find_all(string=re.compile(r"Forward|Midfielder|Defender|Goalkeeper", re.I)):
        parent = el.parent
        if parent:
            meta["position"] = el.strip()
            break

    result["meta"] = meta
    return result


_LABEL_MAP = {
    # Goals
    "goals scored": "goals", "goals": "goals",
    "goal involvement": "goal_involvements",
    "expected goals (xg)": "xg", "expected goals": "xg",
    "non-penalty xg (npxg)": "npxg", "non-penalty xg": "npxg",
    # Shots
    "shots taken": "shots", "shots on target": "shots_on_target",
    "shot conversion rate": "shot_conversion_pct", "shot accuracy": "shot_accuracy_pct",
    # Assists & passing
    "assists": "assists",
    "expected assists (xa)": "xa", "expected assists": "xa",
    "passes": "passes", "successful passes": "successful_passes",
    "pass completion rate": "pass_completion_pct",
    "key passes": "key_passes",
    "crosses": "crosses", "successful crosses": "successful_crosses",
    "cross completion rate": "cross_completion_pct",
    # Dribbling
    "dribbles": "dribbles", "successful dribbles": "successful_dribbles",
    "dribble success rate": "dribble_success_pct",
    # Defending
    "tackles": "tackles", "interceptions": "interceptions",
    "ground duels": "ground_duels", "ground duels won": "ground_duels_won",
    "aerial duels won": "aerial_duels_won",
    "clearances": "clearances", "shots blocked": "shots_blocked",
    "dribbled past": "dribbled_past",
    # Cards & fouls
    "yellow cards": "yellow_cards", "red cards": "red_cards",
    "fouls committed": "fouls_committed", "fouled against": "fouled_against",
    # Minutes
    "minutes": "minutes", "matches played": "matches",
    "matches started": "matches_started",
}


def _canonicalize(label: str) -> str | None:
    clean = label.lower().strip().rstrip(":")
    # Remove footnote markers like ⓘ
    clean = re.sub(r"[^\w\s\-\(\)%/]", "", clean).strip()
    return _LABEL_MAP.get(clean)


def fetch_footystats(
    slug: str,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict | None:
    """Scrape FootyStats player page and return structured stats dict.

    slug examples: "colombia/luis-diaz", "england/harry-kane"
    Returns None if blocked (Cloudflare 403) or unavailable — caller degrades gracefully.
    """
    path = _cache_path(cache_dir, slug)
    if not force_refresh and path.exists():
        try:
            data = json.loads(path.read_text())
            log.info("FootyStats cache hit: %s", path)
            return data
        except Exception:
            pass

    try:
        data = _scrape(slug)
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 403:
            log.info("FootyStats: Cloudflare block for %s (403) — degraded mode", slug)
        else:
            log.warning("FootyStats scrape failed for %s: %s", slug, exc)
        return None
    except Exception as exc:
        log.warning("FootyStats scrape failed for %s: %s", slug, exc)
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    log.info("FootyStats cached to %s", path)
    return data
