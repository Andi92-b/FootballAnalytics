"""
sources/one_versus_one.py — one-versus-one.com HTML scraper.

All 18 tables are scraped. Labels are cleaned by stripping the ⓘ tooltip text
(everything from "ⓘ" onwards), then matched against _LABEL_MAP.

Returns a flat `stats` dict of canonical_key → float.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

_BASE = "https://one-versus-one.com/en/players"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# Maps cleaned OVO label → canonical snake_case key
# "Ariel" is OVO's consistent typo for "Aerial"
_LABEL_MAP: dict[str, str] = {
    # Table 1 — Key Stats
    "Goals":                                              "goals",
    "Assists":                                            "assists",
    "Shots on Goal":                                      "shots_on_goal",
    "Progressive carries (PrgC)":                         "progressive_carries",
    "Successful passes to pitch position opponent box":    "passes_to_opp_box",
    # Table 3 — Advanced Stats
    "Passing accuracy %":                                 "pass_accuracy_pct",
    "Succesful dribbles":                                 "successful_dribbles_ovo",
    "Ball losses % per game":                             "ball_losses_pct",
    "Pre-assists":                                        "pre_assists",
    "Successful passes to pitch position final third":    "passes_to_final_third_ovo",
    "Most fouls":                                         "most_fouls_ovo",
    # Table 6 — Indices
    "1vs1 Index":                                         "index_overall",
    "1vs1 index defensive":                               "index_defensive",
    "1vs1 Index offensive":                               "index_offensive",
    "Offensive interventions":                            "offensive_interventions",
    # Table 7 — Scoring breakdown
    "Average scorer points per game":                     "scorer_points_per_game",
    "Goals by long distance shot":                        "goals_long_distance",
    "Goals by head":                                      "goals_headed_ovo",
    "Penalty goals":                                      "penalty_goals_ovo",
    "Goals by freekick":                                  "goals_freekick_ovo",
    "Goals by foot":                                      "goals_foot_ovo",
    "Chances created":                                    "chances_created_ovo",
    "Big chances":                                        "big_chances_ovo",
    # Table 8 — Passing detail
    "Total successful passes by low pass":                "passes_low_total",
    "Total successful passes by diagonal pass":           "passes_diagonal_total",
    "Total successful passes by throw-ins":               "passes_throw_ins",
    "Total successful passes by corners":                 "passes_corners",
    "Succesful passes in % by low pass":                  "passes_low_pct",
    "Succesful passes in % by diagonal pass":             "passes_diagonal_pct",
    # Table 9 — Touches
    "Offensive touches":                                  "offensive_touches",
    "Offensive touches in phase Set Pieces":              "offensive_touches_set_pieces",
    "Defensive touches in phase Out of Possession":       "defensive_touches_oop",
    "Defensive touches in phase Defensive Transition":    "defensive_touches_def_trans",
    # Table 10 — Ball losses detail
    "Ball losses by low passes":                          "ball_losses_by_low_passes",
    "Ball losses in own box":                             "ball_losses_own_box",
    "Ball losses in first third":                         "ball_losses_first_third",
    "Ball losses in opponent box":                        "ball_losses_opp_box",
    "Ball losses total":                                  "ball_losses_total",
    # Table 11 — Ball regains
    "Ball regains total":                                 "ball_regains",
    "Ball regains in own box":                            "ball_regains_own_box",
    "Ball regains in opponents box":                      "ball_regains_opp_box",
    # Table 12 — Duels
    "Ground duels won":                                   "ground_duels_won",
    "Ground duels lost":                                  "ground_duels_lost",
    "Ariel duels won":                                    "aerial_duels_won",
    "Ariel duels lost":                                   "aerial_duels_lost",
    "Tackles":                                            "tackles_ovo",
    "Clearances by head":                                 "clearances_head",
    "Clearances by foot":                                 "clearances_foot",
    "Ground duels total":                                 "ground_duels_total",
    "Ground duels won %":                                 "ground_duels_won_pct",
    "Ground duels lost %":                                "ground_duels_lost_pct",
    "Ariel duels total":                                  "aerial_duels_total",
    "Ariel duels won %":                                  "aerial_duels_won_pct",
    "Ariel duels lost %":                                 "aerial_duels_lost_pct",
}


def _cache_path(cache_dir: Path, slug: str) -> Path:
    safe = slug.replace("/", "_").replace(" ", "_")
    return cache_dir / "ovo" / f"{safe}.json"


def _parse_number(text: str) -> float | None:
    cleaned = text.strip().replace(",", "").replace("%", "")
    if not cleaned or cleaned in ("-", "N/A", "Locked", "xxxx"):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _clean_label(raw: str) -> str:
    """Strip ⓘ tooltip suffix and surrounding whitespace."""
    return raw.split("\u24d8")[0].strip()


def _scrape(slug: str) -> dict:
    url = f"{_BASE}/{slug}"
    log.info("one-versus-one scraping %s", url)
    resp = requests.get(url, headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    result: dict = {"url": url, "slug": slug, "meta": {}, "stats": {}, "rankings": {}}

    # --- Player metadata ---
    h1 = soup.find("h1")
    if h1:
        result["meta"]["name"] = h1.get_text(strip=True).replace("Stats", "").strip()

    # --- Parse every table: first cell = label, second cell = value ---
    stats: dict[str, float] = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            label = _clean_label(cells[0].get_text(" ", strip=True))
            val = _parse_number(cells[1].get_text(strip=True))
            canonical = _LABEL_MAP.get(label)
            # First-write-wins: prefer earlier tables (key stats over duplicates)
            if canonical and val is not None and canonical not in stats:
                stats[canonical] = val

    result["stats"] = stats

    # --- Rankings ---
    for text_node in soup.find_all(string=re.compile(r"ranking \d+ for", re.I)):
        m = re.search(r"ranking (\d+) for (.+?)(?:\s+in|\s*$)", text_node, re.I)
        if m:
            result["rankings"][m.group(2).strip().lower()] = int(m.group(1))

    return result


def fetch_ovo(
    slug: str,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict | None:
    """Scrape one-versus-one.com player page. slug e.g. 'Luis-Diaz-45145'"""
    path = _cache_path(cache_dir, slug)
    if not force_refresh and path.exists():
        try:
            data = json.loads(path.read_text())
            # Invalidate old-format caches that lack the flat 'stats' key
            if "stats" in data and isinstance(data["stats"], dict):
                log.info("one-versus-one cache hit: %s", path)
                return data
        except Exception:
            pass

    try:
        data = _scrape(slug)
    except Exception as exc:
        log.warning("one-versus-one scrape failed for %s: %s", slug, exc)
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    log.info("one-versus-one cached to %s", path)
    return data
