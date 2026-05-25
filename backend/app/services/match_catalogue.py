"""
Fetches the Bayern München 2025-26 match schedule from Transfermarkt and upserts
into the matches table.  Competitions captured: Bundesliga, Champions League, DFB Pokal.
"""
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from backend import db

TRANSFERMARKT_URL = (
    "https://www.transfermarkt.de/fc-bayern-munchen/spielplan/verein/27/saison_id/2025"
)

COMPETITION_MAP = {
    "1. Bundesliga": "Bundesliga",
    "UEFA Champions League": "Champions League",
    "DFB-Pokal": "DFB Pokal",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


_UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                             "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})


def _slug(date: str, home: str, away: str) -> str:
    def clean(s: str) -> str:
        s = s.translate(_UMLAUT_MAP)
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return f"{date}_{clean(home)}_{clean(away)}"


def _parse_score(score_text: str) -> tuple[int | None, int | None]:
    m = re.search(r"(\d+)\s*:\s*(\d+)", score_text or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def fetch_and_store(timeout: float = 15.0) -> list[dict]:
    """
    Scrape Transfermarkt schedule, upsert into matches table, return list of match dicts.
    Only captures competitions in COMPETITION_MAP.
    """
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
        resp = client.get(TRANSFERMARKT_URL)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    matches: list[dict] = []
    current_competition: str | None = None

    for row in soup.select("table.spielplandaten tr"):
        # Competition header rows have a <th> with the competition name
        comp_cell = row.select_one("td.hauptlink a[href*='wettbewerb']")
        if comp_cell:
            raw = comp_cell.get_text(strip=True)
            current_competition = COMPETITION_MAP.get(raw)
            continue

        if current_competition is None:
            continue

        cells = row.find_all("td")
        if len(cells) < 7:
            continue

        # Column order: Spieltag | Datum | Heim | - | Gast | Ergebnis | …
        date_text = cells[1].get_text(strip=True)
        home_text = cells[2].get_text(strip=True)
        away_text = cells[4].get_text(strip=True)
        score_text = cells[5].get_text(strip=True)

        if not home_text or not away_text:
            continue

        # Normalise date "Fr 15.11.25" → "2025-11-15"
        date_match = re.search(r"(\d{2})\.(\d{2})\.(\d{2,4})", date_text)
        if not date_match:
            continue
        day, month, year = date_match.groups()
        year = f"20{year}" if len(year) == 2 else year
        try:
            iso_date = datetime.strptime(f"{day}.{month}.{year}", "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            continue

        home_goals, away_goals = _parse_score(score_text)
        match_id = _slug(iso_date, home_text, away_text)

        match = {
            "id": match_id,
            "date": iso_date,
            "competition": current_competition,
            "home_team": home_text,
            "away_team": away_text,
            "home_goals": home_goals,
            "away_goals": away_goals,
        }
        db.upsert_match(match)
        matches.append(match)

    return matches
