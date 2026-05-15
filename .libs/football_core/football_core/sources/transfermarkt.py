"""
sources/transfermarkt.py — Transfermarkt player position scraper.

Fetches a player's main position and other positions via:
  1. Quick name search → resolve TM player ID
  2. Player profile page → parse position block

Returns::

    {
        "tm_id": int,
        "tm_slug": str,
        "main_position": str,          # e.g. "Attacking Midfield"
        "main_position_group": str,    # e.g. "Midfield"
        "other_positions": [str],      # e.g. ["Right Winger", "Central Midfield"]
    }

Cache: .cache/transfermarkt/{normalised_name}.json
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

_SEARCH_URL = "https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche"
_PROFILE_BASE = "https://www.transfermarkt.com"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower().strip()


def _safe_filename(s: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", _norm(s))


def _cache_path(cache_dir: Path, player_name: str) -> Path:
    return cache_dir / "transfermarkt" / f"{_safe_filename(player_name)}.json"


def _search(session: requests.Session, player_name: str) -> tuple[int, str, str] | None:
    """Search TM and return (player_id, slug, profile_path) for the top result."""
    try:
        resp = session.get(
            _SEARCH_URL,
            params={"query": player_name},
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.warning("TM search request failed for %s: %s", player_name, exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    links = soup.select('td.hauptlink a[href*="/profil/spieler/"]')
    if not links:
        log.debug("TM search returned no player results for %s", player_name)
        return None

    first = links[0]
    href = first.get("href", "")
    slug_match = re.search(r"/([^/]+)/profil/spieler/(\d+)", href)
    if not slug_match:
        return None

    slug = slug_match.group(1)
    player_id = int(slug_match.group(2))
    profile_path = f"/{slug}/profil/spieler/{player_id}"
    log.debug("TM search hit: %s => id=%d slug=%s", player_name, player_id, slug)
    return player_id, slug, profile_path


def _scrape_positions(session: requests.Session, profile_path: str) -> dict:
    """Fetch TM player profile and extract main + other positions."""
    try:
        resp = session.get(
            f"{_PROFILE_BASE}{profile_path}",
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.warning("TM profile fetch failed for %s: %s", profile_path, exc)
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Position block: div.detail-position__box ─────────────────────────────
    # Structure:
    #   <dt class="detail-position__title">Main position:</dt>
    #   <dd class="detail-position__position">Left Winger</dd>
    #   <dt class="detail-position__title">Other position:</dt>
    #   <dd class="detail-position__position">Right Winger</dd>  (one per position)
    main_position = ""
    main_group = ""
    other_positions: list[str] = []

    pos_box = soup.select_one("div.detail-position__box")
    if pos_box:
        current_label = ""
        for el in pos_box.find_all(["dt", "dd"]):
            tag = el.name
            text = el.get_text(strip=True)
            if tag == "dt":
                current_label = text.lower().rstrip(":")
            elif tag == "dd" and text:
                if "main" in current_label:
                    main_position = text
                elif "other" in current_label:
                    other_positions.append(text)

    # ── Fallback: info-table cell "Position: Group - Specific" ───────────────
    if not main_position:
        cells = soup.select("span.info-table__content")
        for i, cell in enumerate(cells):
            if cell.get_text(strip=True) == "Position:":
                if i + 1 < len(cells):
                    raw = cells[i + 1].get_text(strip=True)
                    parts = [p.strip() for p in raw.split("-")]
                    if len(parts) >= 2:
                        main_group = parts[0]
                        main_position = parts[1]
                    else:
                        main_position = raw
                break

    return {
        "main_position": main_position,
        "main_position_group": main_group,
        "other_positions": other_positions,
    }


def fetch_transfermarkt(
    player_name: str,
    cache_dir: Path,
    force_refresh: bool = False,
) -> dict | None:
    """Fetch Transfermarkt position data for a player.

    Caches results so subsequent calls are instant.
    Returns None on search failure or if no player found.
    """
    path = _cache_path(cache_dir, player_name)
    if not force_refresh and path.exists():
        try:
            cached = json.loads(path.read_text())
            log.debug("TM cache hit: %s", path.name)
            return cached
        except Exception:
            pass

    session = requests.Session()
    search_result = _search(session, player_name)
    if search_result is None:
        log.info("TM: no result for %s", player_name)
        return None

    player_id, slug, profile_path = search_result
    pos_data = _scrape_positions(session, profile_path)
    if not pos_data.get("main_position"):
        log.info("TM: no position data for %s", player_name)
        return None

    result = {
        "tm_id": player_id,
        "tm_slug": slug,
        **pos_data,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    log.info(
        "TM: %s => main=%r others=%r",
        player_name,
        result.get("main_position"),
        result.get("other_positions"),
    )
    return result


# ── Position → pizza bucket mapping ──────────────────────────────────────────

_TM_POSITION_TO_BUCKET: dict[str, str] = {
    # Goalkeeper
    "Goalkeeper": "GK",
    # Defence
    "Centre-Back": "CB",
    "Left-Back": "FB",
    "Right-Back": "FB",
    "Left Wing-Back": "FB",
    "Right Wing-Back": "FB",
    # Midfield
    "Defensive Midfield": "DM",
    "Central Midfield": "CM",
    "Right Midfield": "W",
    "Left Midfield": "W",
    "Attacking Midfield": "AM",
    # Attack
    "Left Winger": "W",
    "Right Winger": "W",
    "Second Striker": "CF",
    "Centre-Forward": "CF",
}


def tm_position_to_bucket(tm_data: dict) -> str | None:
    """Convert Transfermarkt main position to our pizza chart position bucket.

    Returns None if the position isn't mapped (caller should fall back to FBref).
    """
    return _TM_POSITION_TO_BUCKET.get(tm_data.get("main_position", ""))
