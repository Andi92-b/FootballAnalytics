"""
Shared fixtures for the Bayern analysis test suite.

The key fixture is `analysis_db`: it patches ANALYSIS_DB_PATH to a fresh
temporary SQLite file for each test, so tests never touch the real cache.
"""
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

import backend.db as db_module


@pytest.fixture()
def analysis_db(tmp_path: Path):
    """
    Redirect ANALYSIS_DB_PATH to a temp file, initialise the schema,
    and yield the path. Cleaned up automatically by pytest.
    """
    test_db = tmp_path / "test_analysis.db"
    with patch.object(db_module, "ANALYSIS_DB_PATH", test_db):
        db_module.init_analysis_db()
        yield test_db


@pytest.fixture()
def sample_match() -> dict:
    return {
        "id": "2025-11-01_fc-bayer-leverkusen_fc-bayernmuenchen",
        "date": "2025-11-01",
        "competition": "Bundesliga",
        "home_team": "Bayer 04 Leverkusen",
        "away_team": "FC Bayern München",
        "home_goals": 1,
        "away_goals": 3,
    }


@pytest.fixture()
def sample_events(sample_match) -> list[dict]:
    match_id = sample_match["id"]
    return [
        {
            "match_id": match_id,
            "minute": 12,
            "type": "goal",
            "direction": "offensive",
            "situation": "counterattack",
            "trigger": "through_ball",
            "defensive_cover": "1v1",
            "players_involved": '["Müller", "Kane"]',
            "outcome": "goal",
            "description": "Müller spielt Kane frei, der cool verwandelt",
            "confidence": "high",
        },
        {
            "match_id": match_id,
            "minute": 58,
            "type": "chance_conceded",
            "direction": "defensive",
            "situation": "individual_error",
            "trigger": "ball_loss_defensive",
            "defensive_cover": "outnumbered",
            "players_involved": '["Upamecano"]',
            "outcome": "goal",
            "description": "Upamecano verliert den Ball im Aufbau",
            "confidence": "high",
        },
    ]
