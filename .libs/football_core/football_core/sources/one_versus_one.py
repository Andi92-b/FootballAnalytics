"""
sources/one_versus_one.py — one-versus-one.com HTML scraper.

Scrapes the public player stats page to retrieve:
- Key Stats: goals, assists, shots on goal, progressive carries, passes to opp box
- Advanced Stats: passing accuracy %, successful dribbles, ball losses %, pre-assists (if free)

Cache: .cache/ovo/{slug_normalized}.json
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


_KEY_STAT_MAP = {
    "Goals": "goals",
    "Assists": "assists",
    "Shots on Goal": "shots_on_goal",
    "Progressive carries (PrgC)": "progressive_carries",
    "Successful passes to pitch position opponent box": "passes_to_opp_box",
}

_ADV_STAT_MAP = {
    "Passing accuracy %": "pass_accuracy_pct",
    "Succesful dribbles": "successful_dribbles",
    "Ball losses % per game": "ball_losses_pct",
    "Pre-assists": "pre_assists",
    "Ball regains total": "ball_regains",
}


def _scrape(slug: str) -> dict:
    url = f"{_BASE}/{slug}"
    log.info("one-versus-one scraping %s", url)
    resp = requests.get(url, headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    result: dict = {
        "url": url,
        "slug": slug,
        "meta": {},
        "key_stats": {},
        "advanced_stats": {},
        "rankings": {},
    }

    # --- Player metadata ---
    h1 = soup.find("h1")
    if h1:
        result["meta"]["name"] = h1.get_text(strip=True).replace("Stats", "").strip()

    for label_class in ["position", "country", "age"]:
        el = soup.find(class_=re.compile(label_class, re.I))
        if el:
            result["meta"][label_class] = el.get_text(strip=True)

    # --- Key Stats table ---
    # The table has headers METRIC / VALUE
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "METRIC" in headers and "VALUE" in headers:
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    metric = cells[0].get_text(strip=True)
                    value_text = cells[1].get_text(strip=True)
                    val = _parse_number(value_text)
                    canonical = _KEY_STAT_MAP.get(metric)
                    if canonical and val is not None:
                        result["key_stats"][canonical] = val

    # --- Advanced Stats table (same structure) ---
    # The page has multiple tables — iterate all and try advanced stat labels
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                metric = cells[0].get_text(strip=True)
                value_text = cells[1].get_text(strip=True)
                val = _parse_number(value_text)
                canonical = _ADV_STAT_MAP.get(metric)
                if canonical and val is not None:
                    result["advanced_stats"][canonical] = val

    # --- News/insights snippets (free text bullet points) ---
    insights = []
    for bullet in soup.find_all(class_=re.compile(r"stat-slip|news|insight", re.I)):
        text = bullet.get_text(strip=True)
        if len(text) > 20:
            insights.append(text)
    result["insights"] = insights[:10]  # cap at 10

    # --- Rankings mentioned inline ---
    # e.g. "ranking 4 for total goals scored"
    for text_node in soup.find_all(string=re.compile(r"ranking \d+ for", re.I)):
        m = re.search(r"ranking (\d+) for (.+?)(?:\s+in|\s*$)", text_node, re.I)
        if m:
            rank = int(m.group(1))
            stat_name = m.group(2).strip().lower()
            result["rankings"][stat_name] = rank

    return result


def fetch_ovo(
    slug: str,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict | None:
    """Scrape one-versus-one.com player page.

    slug example: "Luis-Diaz-45145"
    """
    path = _cache_path(cache_dir, slug)
    if not force_refresh and path.exists():
        try:
            data = json.loads(path.read_text())
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
