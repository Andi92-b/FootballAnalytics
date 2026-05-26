"""
Tests for backend/app/services/match_data_fetcher.py.

All HTTP calls are intercepted with respx. DB writes go to a temp SQLite.
"""
from pathlib import Path
from unittest.mock import patch

import pytest
import respx
from httpx import Response

import backend.db as db_module
from backend.app.services import match_data_fetcher

# ── Minimal Understat team page ───────────────────────────────────────────────

def _make_understat_page(entries: list[dict]) -> str:
    import json, html
    data_str = html.escape(json.dumps(entries))
    return f"""<!DOCTYPE html>
<html><body>
<script>
var datesData = JSON.parse('{data_str}');
</script>
</body></html>"""


UNDERSTAT_HOME_ENTRY = {
    "id": "18888",
    "isResult": True,
    "datetime": "2025-08-22 18:30:00",
    "side": "h",
    "h": {"id": "12", "title": "Bayern Munich", "short_title": "BAY"},
    "a": {"id": "67", "title": "Hamburger SV", "short_title": "HSV"},
    "goals": {"h": "4", "a": "0"},
    "xG": {"h": "2.5432", "a": "0.8765"},
    "result": "w",
}

UNDERSTAT_AWAY_ENTRY = {
    "id": "18999",
    "isResult": True,
    "datetime": "2025-08-30 15:30:00",
    "side": "a",
    "h": {"id": "22", "title": "Bayer Leverkusen", "short_title": "B04"},
    "a": {"id": "12", "title": "Bayern Munich", "short_title": "BAY"},
    "goals": {"h": "1", "a": "3"},
    "xG": {"h": "1.1234", "a": "2.7890"},
    "result": "w",
}

UNDERSTAT_FUTURE_ENTRY = {
    "id": "19000",
    "isResult": False,
    "datetime": "2026-08-01 15:30:00",
    "side": "h",
    "h": {"id": "12", "title": "Bayern Munich", "short_title": "BAY"},
    "a": {"id": "55", "title": "Borussia Dortmund", "short_title": "BVB"},
    "goals": {"h": "", "a": ""},
    "xG": {"h": "", "a": ""},
    "result": "",
}

UNDERSTAT_URL_PATTERN = f"https://understat.com/team/{match_data_fetcher.UNDERSTAT_TEAM_SLUG}/"


class TestUnderstatPageParser:
    def test_parses_home_match(self):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY])
        matches = match_data_fetcher._parse_understat_page(page)
        assert len(matches) == 1
        m = matches[0]
        assert m["home_team"] == "Bayern Munich"
        assert m["away_team"] == "Hamburger SV"
        assert m["home_goals"] == 4
        assert m["away_goals"] == 0
        assert m["competition"] == "Bundesliga"

    def test_parses_away_match(self):
        page = _make_understat_page([UNDERSTAT_AWAY_ENTRY])
        matches = match_data_fetcher._parse_understat_page(page)
        assert len(matches) == 1
        m = matches[0]
        assert m["home_team"] == "Bayer Leverkusen"
        assert m["away_team"] == "Bayern Munich"
        assert m["home_goals"] == 1
        assert m["away_goals"] == 3

    def test_parses_xg_values(self):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY])
        matches = match_data_fetcher._parse_understat_page(page)
        m = matches[0]
        assert abs(m["home_xg"] - 2.5432) < 0.001
        assert abs(m["away_xg"] - 0.8765) < 0.001

    def test_filters_future_matches(self):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY, UNDERSTAT_FUTURE_ENTRY])
        matches = match_data_fetcher._parse_understat_page(page)
        assert len(matches) == 1

    def test_iso_date_format(self):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY])
        matches = match_data_fetcher._parse_understat_page(page)
        date = matches[0]["date"]
        parts = date.split("-")
        assert len(parts) == 3 and len(parts[0]) == 4

    def test_empty_page_returns_empty_list(self):
        matches = match_data_fetcher._parse_understat_page("<html><body></body></html>")
        assert matches == []

    def test_slug_format(self):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY])
        matches = match_data_fetcher._parse_understat_page(page)
        assert "2025-08-22" in matches[0]["id"]

    def test_multiple_matches_parsed(self):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY, UNDERSTAT_AWAY_ENTRY])
        matches = match_data_fetcher._parse_understat_page(page)
        assert len(matches) == 2

    def test_xg_none_for_missing_values(self):
        entry = {**UNDERSTAT_FUTURE_ENTRY, "isResult": True, "goals": {"h": "2", "a": "1"}, "xG": {"h": "", "a": ""}}
        page = _make_understat_page([entry])
        matches = match_data_fetcher._parse_understat_page(page)
        m = matches[0]
        assert m["home_xg"] is None
        assert m["away_xg"] is None


class TestFetchUnderstatMatches:
    @respx.mock
    def test_fetches_and_returns_matches(self, tmp_path: Path):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY, UNDERSTAT_AWAY_ENTRY])
        respx.get(f"{UNDERSTAT_URL_PATTERN}2025").mock(return_value=Response(200, text=page))
        matches = match_data_fetcher.fetch_understat_matches(2025, tmp_path)
        assert len(matches) == 2

    @respx.mock
    def test_caches_results(self, tmp_path: Path):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY])
        respx.get(f"{UNDERSTAT_URL_PATTERN}2025").mock(return_value=Response(200, text=page))
        match_data_fetcher.fetch_understat_matches(2025, tmp_path)
        # Second call should use cache — mock would raise if called again
        respx.get(f"{UNDERSTAT_URL_PATTERN}2025").mock(side_effect=Exception("should not fetch"))
        matches = match_data_fetcher.fetch_understat_matches(2025, tmp_path)
        assert len(matches) == 1

    @respx.mock
    def test_force_refresh_bypasses_cache(self, tmp_path: Path):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY])
        respx.get(f"{UNDERSTAT_URL_PATTERN}2025").mock(return_value=Response(200, text=page))
        match_data_fetcher.fetch_understat_matches(2025, tmp_path)
        # Force refresh with 2 entries now
        page2 = _make_understat_page([UNDERSTAT_HOME_ENTRY, UNDERSTAT_AWAY_ENTRY])
        respx.get(f"{UNDERSTAT_URL_PATTERN}2025").mock(return_value=Response(200, text=page2))
        matches = match_data_fetcher.fetch_understat_matches(2025, tmp_path, force_refresh=True)
        assert len(matches) == 2

    @respx.mock
    def test_raises_on_http_error(self, tmp_path: Path):
        respx.get(f"{UNDERSTAT_URL_PATTERN}2025").mock(return_value=Response(503))
        with pytest.raises(Exception):
            match_data_fetcher.fetch_understat_matches(2025, tmp_path)


class TestMergeMatches:
    def _m(self, date: str, home: str, away: str, **kw) -> dict:
        from backend.app.services.match_catalogue import _slug
        return {
            "id": _slug(date, home, away),
            "date": date,
            "competition": "Bundesliga",
            "home_team": home,
            "away_team": away,
            "home_goals": kw.get("home_goals"),
            "away_goals": kw.get("away_goals"),
            "home_xg": kw.get("home_xg"),
            "away_xg": kw.get("away_xg"),
        }

    def test_no_duplicates_same_match(self):
        m1 = self._m("2025-08-22", "Bayern", "Hamburg", home_goals=4, away_goals=0)
        m2 = self._m("2025-08-22", "Bayern", "Hamburg", home_goals=4, away_goals=0)
        merged = match_data_fetcher._merge_matches([m1], [m2])
        assert len(merged) == 1

    def test_understat_xg_preferred(self):
        fbref = self._m("2025-08-22", "Bayern", "Hamburg", home_xg=2.0)
        understat = self._m("2025-08-22", "Bayern", "Hamburg", home_xg=2.54)
        merged = match_data_fetcher._merge_matches([understat], [fbref])
        assert len(merged) == 1
        assert merged[0]["home_xg"] == pytest.approx(2.54)

    def test_fbref_only_match_included(self):
        fbref = self._m("2025-09-16", "Bayern", "Dinamo Zagreb", home_goals=9, away_goals=2)
        fbref["competition"] = "Champions League"
        merged = match_data_fetcher._merge_matches([], [fbref])
        assert len(merged) == 1
        assert merged[0]["competition"] == "Champions League"

    def test_unique_matches_both_sources(self):
        m1 = self._m("2025-08-22", "Bayern", "Hamburg")
        m2 = self._m("2025-09-13", "Bayern", "Dortmund")
        merged = match_data_fetcher._merge_matches([m1], [m2])
        assert len(merged) == 2


class TestFetchAndStore:
    @respx.mock
    def test_upserts_matches_to_db(self, analysis_db: Path, tmp_path: Path):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY, UNDERSTAT_AWAY_ENTRY])
        respx.get(f"{UNDERSTAT_URL_PATTERN}2025").mock(return_value=Response(200, text=page))
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            result = match_data_fetcher.fetch_and_store(season=2025, cache_dir=tmp_path)
        assert result["upserted"] >= 2
        assert "understat" in result["sources"]

    @respx.mock
    def test_idempotent_double_fetch(self, analysis_db: Path, tmp_path: Path):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY])
        respx.get(f"{UNDERSTAT_URL_PATTERN}2025").mock(return_value=Response(200, text=page))
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            match_data_fetcher.fetch_and_store(season=2025, cache_dir=tmp_path)
            match_data_fetcher.fetch_and_store(season=2025, cache_dir=tmp_path)
            stored = db_module.list_matches()
        assert len(stored) == 1

    @respx.mock
    def test_xg_stored_in_match(self, analysis_db: Path, tmp_path: Path):
        page = _make_understat_page([UNDERSTAT_HOME_ENTRY])
        respx.get(f"{UNDERSTAT_URL_PATTERN}2025").mock(return_value=Response(200, text=page))
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            match_data_fetcher.fetch_and_store(season=2025, cache_dir=tmp_path)
            matches = db_module.list_matches()
        assert len(matches) == 1
        m = matches[0]
        assert m["home_xg"] is not None
        assert abs(m["home_xg"] - 2.5432) < 0.001

    @respx.mock
    def test_understat_error_returns_zero_upserted(self, analysis_db: Path, tmp_path: Path):
        respx.get(f"{UNDERSTAT_URL_PATTERN}2025").mock(return_value=Response(503))
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            result = match_data_fetcher.fetch_and_store(season=2025, cache_dir=tmp_path)
        assert result["upserted"] == 0
        assert result["sources"] == []
