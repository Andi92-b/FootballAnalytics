"""
Fetches and stores match text from Kicker (live ticker + report) and SZ (manual HTML drops).
UEFA.com scraping is intentionally deferred — CL matches handled via SZ / Kicker where available.
"""
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from backend import db

SZ_CACHE_DIR = Path(__file__).parents[4] / ".cache" / "sz_articles"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


# ── Kicker ────────────────────────────────────────────────────────────────────

def _kicker_slug(team: str) -> str:
    replacements = {
        "FC Bayern München": "fc-bayern-muenchen",
        "Bayern München": "fc-bayern-muenchen",
        "Bayer 04 Leverkusen": "bayer-leverkusen",
        "Borussia Dortmund": "bvb-dortmund",
        "RB Leipzig": "rb-leipzig",
        "Eintracht Frankfurt": "eintracht-frankfurt",
        "VfB Stuttgart": "vfb-stuttgart",
        "SC Freiburg": "sc-freiburg",
        "TSG Hoffenheim": "tsg-hoffenheim",
        "Werder Bremen": "sv-werder-bremen",
        "1. FC Union Berlin": "union-berlin",
        "VfL Wolfsburg": "vfl-wolfsburg",
        "Borussia Mönchengladbach": "borussia-moenchengladbach",
        "FC Augsburg": "fc-augsburg",
        "1. FC Köln": "1-fc-koeln",
        "1. FSV Mainz 05": "1-fsv-mainz-05",
        "FC St. Pauli": "fc-st-pauli",
        "Holstein Kiel": "holstein-kiel",
    }
    if team in replacements:
        return replacements[team]
    return re.sub(r"[^a-z0-9]+", "-", team.lower()).strip("-")


def _comp_slug(competition: str) -> str:
    return {
        "Bundesliga": "bundesliga",
        "Champions League": "champions-league",
        "DFB Pokal": "dfb-pokal",
    }.get(competition, "bundesliga")


def scrape_kicker_ticker(match: dict, timeout: float = 15.0) -> str | None:
    """
    Fetch the Kicker live ticker for a match.
    Returns extracted text on success, None if the page could not be retrieved.
    Stores result in text_sources table.
    """
    home_slug = _kicker_slug(match["home_team"])
    away_slug = _kicker_slug(match["away_team"])
    comp_slug = _comp_slug(match["competition"])
    date = match["date"]  # YYYY-MM-DD

    # Kicker ticker URL: /home-gegen-away/liveticker/competition/season/round
    # The match-specific round ID is unknown ahead of time, so we search Google first.
    search_url = (
        f"https://www.kicker.de/{home_slug}-gegen-{away_slug}"
        f"/liveticker/{comp_slug}"
    )

    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
            resp = client.get(search_url)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
    except httpx.HTTPError:
        return None

    entries = soup.select(".timeline-entry, .ticker-entry, [class*='ticker']")
    if not entries:
        # Fallback: grab all paragraphs inside main content
        entries = soup.select("main p, article p")

    text_blocks: list[str] = []
    for entry in entries:
        minute_el = entry.select_one("[class*='minute'], [class*='time']")
        minute = minute_el.get_text(strip=True) if minute_el else ""
        body = entry.get_text(separator=" ", strip=True)
        if body:
            text_blocks.append(f"[{minute}] {body}" if minute else body)

    content = "\n".join(text_blocks)
    if content:
        db.insert_text_source(match["id"], "kicker_ticker", content)
    return content or None


def scrape_kicker_report(match: dict, timeout: float = 15.0) -> str | None:
    """
    Fetch the Kicker Spielbericht (match report).
    Returns extracted text on success, None otherwise.
    Stores result in text_sources table.
    """
    home_slug = _kicker_slug(match["home_team"])
    away_slug = _kicker_slug(match["away_team"])
    comp_slug = _comp_slug(match["competition"])

    report_url = (
        f"https://www.kicker.de/{home_slug}-gegen-{away_slug}"
        f"/spielbericht/{comp_slug}"
    )

    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
            resp = client.get(report_url)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
    except httpx.HTTPError:
        return None

    article = soup.select_one("article, .article-body, [class*='matchreport'], main")
    if not article:
        return None

    paragraphs = [p.get_text(separator=" ", strip=True) for p in article.select("p") if p.get_text(strip=True)]
    content = "\n\n".join(paragraphs)
    if content:
        db.insert_text_source(match["id"], "kicker_report", content)
    return content or None


# ── SZ file loader ────────────────────────────────────────────────────────────

def load_sz_files(match: dict) -> str | None:
    """
    Load manually downloaded SZ HTML files from .cache/sz_articles/{match_id}*.html.
    Returns combined text on success, None if no files found.
    Stores result in text_sources table.
    """
    SZ_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(SZ_CACHE_DIR.glob(f"{match['id']}*.html"))
    if not files:
        return None

    all_text: list[str] = []
    for f in files:
        soup = BeautifulSoup(f.read_text(encoding="utf-8", errors="replace"), "html.parser")
        article = soup.select_one("article, [class*='article-body'], main")
        if not article:
            article = soup.body
        if article:
            paragraphs = [p.get_text(separator=" ", strip=True) for p in article.select("p") if p.get_text(strip=True)]
            all_text.extend(paragraphs)

    content = "\n\n".join(all_text)
    if content:
        db.insert_text_source(match["id"], "sz", content)
    return content or None


def fetch_all_text(match: dict) -> dict[str, str | None]:
    """Convenience: fetch all available text sources for a match."""
    return {
        "kicker_ticker": scrape_kicker_ticker(match),
        "kicker_report": scrape_kicker_report(match),
        "sz": load_sz_files(match),
    }
