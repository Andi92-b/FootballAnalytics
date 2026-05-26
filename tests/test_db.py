"""
Tests for backend/db.py — analysis tables schema, CRUD helpers, and constraints.
All tests use the `analysis_db` fixture (isolated temp SQLite; never touches real cache).
"""
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

import backend.db as db_module
from backend import db


# ── Schema ─────────────────────────────────────────────────────────────────────

class TestSchema:
    def test_all_tables_created(self, analysis_db: Path):
        conn = sqlite3.connect(analysis_db)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert {"matches", "match_shots", "text_sources", "match_events"}.issubset(tables)

    def test_matches_columns(self, analysis_db: Path):
        conn = sqlite3.connect(analysis_db)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(matches)").fetchall()}
        conn.close()
        assert cols >= {"id", "date", "competition", "home_team", "away_team",
                        "home_goals", "away_goals", "analysed"}

    def test_match_events_columns(self, analysis_db: Path):
        conn = sqlite3.connect(analysis_db)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(match_events)").fetchall()}
        conn.close()
        assert cols >= {"id", "match_id", "minute", "type", "direction",
                        "situation", "trigger", "players_involved",
                        "outcome", "description", "confidence"}

    def test_analysed_defaults_to_zero(self, analysis_db: Path):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match({
                "id": "test-match",
                "date": "2025-08-01",
                "competition": "Bundesliga",
                "home_team": "Team A",
                "away_team": "FC Bayern München",
                "home_goals": None,
                "away_goals": None,
            })
            m = db.get_match("test-match")
        assert m["analysed"] == 0

    def test_indexes_exist(self, analysis_db: Path):
        conn = sqlite3.connect(analysis_db)
        indexes = {r[1] for r in conn.execute(
            "SELECT type, name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        conn.close()
        assert "idx_match_events_match" in indexes
        assert "idx_text_sources_match" in indexes
        assert "idx_match_shots_match" in indexes


# ── Matches CRUD ───────────────────────────────────────────────────────────────

class TestMatchesCRUD:
    def test_upsert_and_get(self, analysis_db: Path, sample_match: dict):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            result = db.get_match(sample_match["id"])
        assert result is not None
        assert result["home_team"] == sample_match["home_team"]
        assert result["home_goals"] == 1
        assert result["away_goals"] == 3

    def test_get_nonexistent_returns_none(self, analysis_db: Path):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            result = db.get_match("does-not-exist")
        assert result is None

    def test_upsert_is_idempotent(self, analysis_db: Path, sample_match: dict):
        updated = {**sample_match, "home_goals": 2, "away_goals": 4}
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.upsert_match(updated)   # second upsert should update, not duplicate
            result = db.get_match(sample_match["id"])
        assert result["home_goals"] == 2
        assert result["away_goals"] == 4

    def test_list_matches_all(self, analysis_db: Path, sample_match: dict):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            cl_match = {**sample_match, "id": "cl-match", "competition": "Champions League"}
            db.upsert_match(cl_match)
            results = db.list_matches()
        assert len(results) == 2

    def test_list_matches_filtered_by_competition(self, analysis_db: Path, sample_match: dict):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            cl_match = {**sample_match, "id": "cl-match", "competition": "Champions League"}
            db.upsert_match(cl_match)
            results = db.list_matches(competition="Bundesliga")
        assert len(results) == 1
        assert results[0]["competition"] == "Bundesliga"

    def test_mark_analysed(self, analysis_db: Path, sample_match: dict):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.mark_match_analysed(sample_match["id"])
            result = db.get_match(sample_match["id"])
        assert result["analysed"] == 1

    def test_list_ordered_by_date_desc(self, analysis_db: Path):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            for date in ["2025-09-01", "2025-11-01", "2025-10-01"]:
                db.upsert_match({
                    "id": f"match-{date}", "date": date,
                    "competition": "Bundesliga",
                    "home_team": "A", "away_team": "B",
                    "home_goals": None, "away_goals": None,
                })
            results = db.list_matches()
        assert results[0]["date"] == "2025-11-01"
        assert results[-1]["date"] == "2025-09-01"


# ── Text Sources CRUD ──────────────────────────────────────────────────────────

class TestTextSourcesCRUD:
    def test_insert_and_get(self, analysis_db: Path, sample_match: dict):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.insert_text_source(sample_match["id"], "kicker_ticker", "Ticker content here")
            sources = db.get_text_sources(sample_match["id"])
        assert len(sources) == 1
        assert sources[0]["source"] == "kicker_ticker"
        assert sources[0]["content"] == "Ticker content here"

    def test_multiple_sources(self, analysis_db: Path, sample_match: dict):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.insert_text_source(sample_match["id"], "kicker_ticker", "Ticker")
            db.insert_text_source(sample_match["id"], "kicker_report", "Report")
            db.insert_text_source(sample_match["id"], "sz", "SZ article")
            sources = db.get_text_sources(sample_match["id"])
        assert len(sources) == 3
        source_types = {s["source"] for s in sources}
        assert source_types == {"kicker_ticker", "kicker_report", "sz"}

    def test_fetched_at_is_set(self, analysis_db: Path, sample_match: dict):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.insert_text_source(sample_match["id"], "kicker_ticker", "text")
            sources = db.get_text_sources(sample_match["id"])
        assert sources[0]["fetched_at"] is not None
        assert "T" in sources[0]["fetched_at"]  # ISO-8601 format


# ── Match Events CRUD ──────────────────────────────────────────────────────────

class TestMatchEventsCRUD:
    def test_insert_and_get(self, analysis_db: Path, sample_match: dict, sample_events: list):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.insert_match_events(sample_events)
            results = db.get_match_events(sample_match["id"])
        assert len(results) == 2

    def test_events_ordered_by_minute(self, analysis_db: Path, sample_match: dict, sample_events: list):
        # Insert in reverse minute order to test ordering
        reversed_events = list(reversed(sample_events))
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.insert_match_events(reversed_events)
            results = db.get_match_events(sample_match["id"])
        assert results[0]["minute"] == 12
        assert results[1]["minute"] == 58

    def test_event_fields_preserved(self, analysis_db: Path, sample_match: dict, sample_events: list):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.insert_match_events([sample_events[0]])
            ev = db.get_match_events(sample_match["id"])[0]
        assert ev["type"] == "goal"
        assert ev["direction"] == "offensive"
        assert ev["situation"] == "counterattack"
        assert ev["confidence"] == "high"
        assert "Müller" in ev["players_involved"]

    def test_get_all_events_direction_filter(self, analysis_db: Path, sample_match: dict, sample_events: list):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.insert_match_events(sample_events)
            offensive = db.get_all_events(direction="offensive")
            defensive = db.get_all_events(direction="defensive")
        assert all(e["direction"] == "offensive" for e in offensive)
        assert all(e["direction"] == "defensive" for e in defensive)

    def test_get_all_events_competition_filter(self, analysis_db: Path, sample_match: dict, sample_events: list):
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.insert_match_events(sample_events)
            bl_events = db.get_all_events(competition="Bundesliga")
            cl_events = db.get_all_events(competition="Champions League")
        assert len(bl_events) == 2
        assert len(cl_events) == 0


# ── Match Shots CRUD ───────────────────────────────────────────────────────────

class TestMatchShotsCRUD:
    def test_insert_and_get(self, analysis_db: Path, sample_match: dict):
        shots = [
            {"match_id": sample_match["id"], "x": 85.3, "y": 34.1, "xG": 0.23,
             "result": "Goal", "situation": "OpenPlay", "shot_type": "RightFoot",
             "minute": 12, "player": "Kane", "team": "Bayern"},
            {"match_id": sample_match["id"], "x": 91.0, "y": 50.0, "xG": 0.61,
             "result": "SavedShot", "situation": "OpenPlay", "shot_type": "Head",
             "minute": 78, "player": "Müller", "team": "Bayern"},
        ]
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db.upsert_match(sample_match)
            db.insert_match_shots(shots)
            results = db.get_match_shots(sample_match["id"])
        assert len(results) == 2
        assert results[0]["player"] == "Kane"
        assert abs(results[0]["xG"] - 0.23) < 0.001
