"""
Seeds the analysis DB with a representative Bayern München 2025-26 fixture list.

Covers the full season: 34 Bundesliga, 13 Champions League (incl. final),
5 DFB Pokal (incl. final) = 52 matches.

Use this for development, CI, or when Transfermarkt is inaccessible (cloud/CI IPs
are blocked by Cloudflare). Data represents a realistic but illustrative season —
replace with live data once you can run fetch_and_store() from a residential IP.

Usage:
    python -m backend.scripts.seed_db              # seed all
    python -m backend.scripts.seed_db --clear      # wipe matches first, then seed
"""
import argparse
import sqlite3
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[3] / ".env")
except ImportError:
    pass

from backend import db

# fmt: off
FIXTURES: list[dict] = [
    # ── Bundesliga ─────────────────────────────────────────────────────────────
    {"date": "2025-08-22", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "Hamburger SV",              "home_goals": 4, "away_goals": 0},
    {"date": "2025-08-30", "competition": "Bundesliga",        "home_team": "Bayer 04 Leverkusen",     "away_team": "FC Bayern München",          "home_goals": 1, "away_goals": 3},
    {"date": "2025-09-13", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "Borussia Dortmund",          "home_goals": 3, "away_goals": 1},
    {"date": "2025-09-20", "competition": "Bundesliga",        "home_team": "RB Leipzig",              "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 2},
    {"date": "2025-09-27", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "Eintracht Frankfurt",        "home_goals": 5, "away_goals": 1},
    {"date": "2025-10-04", "competition": "Bundesliga",        "home_team": "VfB Stuttgart",           "away_team": "FC Bayern München",          "home_goals": 1, "away_goals": 2},
    {"date": "2025-10-18", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "SC Freiburg",                "home_goals": 3, "away_goals": 0},
    {"date": "2025-10-25", "competition": "Bundesliga",        "home_team": "TSG Hoffenheim",          "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 4},
    {"date": "2025-11-01", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "Werder Bremen",              "home_goals": 2, "away_goals": 0},
    {"date": "2025-11-08", "competition": "Bundesliga",        "home_team": "Borussia Mönchengladbach","away_team": "FC Bayern München",          "home_goals": 1, "away_goals": 3},
    {"date": "2025-11-22", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "VfL Wolfsburg",              "home_goals": 4, "away_goals": 1},
    {"date": "2025-11-29", "competition": "Bundesliga",        "home_team": "FC Augsburg",             "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 3},
    {"date": "2025-12-06", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "1. FSV Mainz 05",            "home_goals": 2, "away_goals": 2},
    {"date": "2025-12-13", "competition": "Bundesliga",        "home_team": "1. FC Union Berlin",      "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 2},
    {"date": "2025-12-20", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "FC St. Pauli",               "home_goals": 6, "away_goals": 0},
    {"date": "2026-01-10", "competition": "Bundesliga",        "home_team": "Borussia Dortmund",       "away_team": "FC Bayern München",          "home_goals": 1, "away_goals": 2},
    {"date": "2026-01-17", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "Bayer 04 Leverkusen",        "home_goals": 3, "away_goals": 1},
    {"date": "2026-01-31", "competition": "Bundesliga",        "home_team": "Eintracht Frankfurt",     "away_team": "FC Bayern München",          "home_goals": 2, "away_goals": 2},
    {"date": "2026-02-07", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "RB Leipzig",                 "home_goals": 2, "away_goals": 0},
    {"date": "2026-02-14", "competition": "Bundesliga",        "home_team": "Werder Bremen",           "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 3},
    {"date": "2026-02-21", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "VfB Stuttgart",              "home_goals": 3, "away_goals": 0},
    {"date": "2026-02-28", "competition": "Bundesliga",        "home_team": "SC Freiburg",             "away_team": "FC Bayern München",          "home_goals": 1, "away_goals": 2},
    {"date": "2026-03-07", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "Borussia Mönchengladbach",   "home_goals": 4, "away_goals": 0},
    {"date": "2026-03-14", "competition": "Bundesliga",        "home_team": "VfL Wolfsburg",           "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 3},
    {"date": "2026-03-21", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "TSG Hoffenheim",             "home_goals": 5, "away_goals": 0},
    {"date": "2026-04-04", "competition": "Bundesliga",        "home_team": "1. FSV Mainz 05",         "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 1},
    {"date": "2026-04-11", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "FC Augsburg",                "home_goals": 3, "away_goals": 1},
    {"date": "2026-04-18", "competition": "Bundesliga",        "home_team": "Hamburger SV",            "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 4},
    {"date": "2026-04-25", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "1. FC Union Berlin",         "home_goals": 2, "away_goals": 0},
    {"date": "2026-05-02", "competition": "Bundesliga",        "home_team": "FC St. Pauli",            "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 5},
    {"date": "2026-05-09", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "FC Augsburg",                "home_goals": 3, "away_goals": 0},
    {"date": "2026-05-16", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "Hamburger SV",               "home_goals": 2, "away_goals": 1},
    {"date": "2026-05-23", "competition": "Bundesliga",        "home_team": "Borussia Dortmund",       "away_team": "FC Bayern München",          "home_goals": 2, "away_goals": 3},
    {"date": "2026-05-23", "competition": "Bundesliga",        "home_team": "FC Bayern München",       "away_team": "SC Freiburg",                "home_goals": 3, "away_goals": 1},

    # ── Champions League ────────────────────────────────────────────────────────
    {"date": "2025-09-16", "competition": "Champions League",  "home_team": "FC Bayern München",       "away_team": "GNK Dinamo Zagreb",          "home_goals": 9, "away_goals": 2},
    {"date": "2025-10-01", "competition": "Champions League",  "home_team": "Aston Villa",             "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 1},
    {"date": "2025-10-22", "competition": "Champions League",  "home_team": "FC Bayern München",       "away_team": "Benfica",                    "home_goals": 1, "away_goals": 0},
    {"date": "2025-11-05", "competition": "Champions League",  "home_team": "Paris Saint-Germain",     "away_team": "FC Bayern München",          "home_goals": 1, "away_goals": 0},
    {"date": "2025-11-26", "competition": "Champions League",  "home_team": "FC Bayern München",       "away_team": "Feyenoord",                  "home_goals": 3, "away_goals": 0},
    {"date": "2025-12-10", "competition": "Champions League",  "home_team": "Shakhtar Donetsk",        "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 5},
    {"date": "2026-01-21", "competition": "Champions League",  "home_team": "FC Bayern München",       "away_team": "Slovan Bratislava",          "home_goals": 7, "away_goals": 0},
    {"date": "2026-01-28", "competition": "Champions League",  "home_team": "Sparta Praha",            "away_team": "FC Bayern München",          "home_goals": 0, "away_goals": 4},
    {"date": "2026-03-04", "competition": "Champions League",  "home_team": "FC Bayern München",       "away_team": "Real Madrid",                "home_goals": 3, "away_goals": 2},
    {"date": "2026-03-11", "competition": "Champions League",  "home_team": "Real Madrid",             "away_team": "FC Bayern München",          "home_goals": 2, "away_goals": 1},
    {"date": "2026-04-07", "competition": "Champions League",  "home_team": "FC Bayern München",       "away_team": "Arsenal FC",                 "home_goals": 2, "away_goals": 0},
    {"date": "2026-04-14", "competition": "Champions League",  "home_team": "Arsenal FC",              "away_team": "FC Bayern München",          "home_goals": 1, "away_goals": 1},
    # Bayern advance 3–1 on aggregate → CL Final
    {"date": "2026-05-27", "competition": "Champions League",  "home_team": "FC Bayern München",       "away_team": "Paris Saint-Germain",        "home_goals": 2, "away_goals": 1},

    # ── DFB Pokal ───────────────────────────────────────────────────────────────
    {"date": "2025-10-29", "competition": "DFB Pokal",         "home_team": "FC Bayern München",       "away_team": "Alemannia Aachen",           "home_goals": 6, "away_goals": 0},
    {"date": "2026-01-07", "competition": "DFB Pokal",         "home_team": "FC Bayern München",       "away_team": "Borussia Dortmund",          "home_goals": 3, "away_goals": 1},
    {"date": "2026-03-03", "competition": "DFB Pokal",         "home_team": "FC Bayern München",       "away_team": "Bayer 04 Leverkusen",        "home_goals": 2, "away_goals": 1},
    {"date": "2026-04-22", "competition": "DFB Pokal",         "home_team": "FC Bayern München",       "away_team": "Eintracht Frankfurt",        "home_goals": 3, "away_goals": 0},
    # Bayern advance → DFB Pokal Final (Olympiastadion Berlin)
    {"date": "2026-05-23", "competition": "DFB Pokal",         "home_team": "FC Bayern München",       "away_team": "RB Leipzig",                 "home_goals": 3, "away_goals": 0},
]
# fmt: on


def _make_id(m: dict) -> str:
    from backend.app.services.match_catalogue import _slug
    return _slug(m["date"], m["home_team"], m["away_team"])


def seed(clear: bool = False) -> int:
    db.init_analysis_db()

    if clear:
        with sqlite3.connect(db.ANALYSIS_DB_PATH) as conn:
            conn.execute("DELETE FROM match_events")
            conn.execute("DELETE FROM match_shots")
            conn.execute("DELETE FROM text_sources")
            conn.execute("DELETE FROM matches")
        print("Database cleared.")

    count = 0
    for fixture in FIXTURES:
        match = {**fixture, "id": _make_id(fixture)}
        db.upsert_match(match)
        count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed analysis DB with Bayern 2025-26 fixtures")
    parser.add_argument("--clear", action="store_true", help="Wipe existing matches before seeding")
    args = parser.parse_args()

    n = seed(clear=args.clear)
    print(f"Seeded {n} matches into {db.ANALYSIS_DB_PATH}")


if __name__ == "__main__":
    main()
