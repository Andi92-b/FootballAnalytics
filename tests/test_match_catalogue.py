"""
Tests for backend/app/services/match_catalogue.py.

HTTP calls are intercepted with respx so no network access is needed.
The DB writes are redirected to a temp SQLite via the analysis_db fixture.
"""
from pathlib import Path
from unittest.mock import patch

import pytest
import respx
from httpx import Response

import backend.db as db_module
from backend.app.services import match_catalogue


# Minimal HTML that mimics the Transfermarkt spielplan table structure.
# Uses the same CSS classes the scraper targets.
FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<body>
<table class="spielplandaten">
  <tbody>
    <!-- Bundesliga block -->
    <tr>
      <td class="hauptlink">
        <a href="/wettbewerb/L1">1. Bundesliga</a>
      </td>
    </tr>
    <tr>
      <td>1</td>
      <td>Fr 23.08.25</td>
      <td>Werder Bremen</td>
      <td>-</td>
      <td>FC Bayern München</td>
      <td>0:3</td>
      <td></td>
    </tr>
    <tr>
      <td>2</td>
      <td>Sa 14.09.25</td>
      <td>FC Bayern München</td>
      <td>-</td>
      <td>Bayer 04 Leverkusen</td>
      <td>2:1</td>
      <td></td>
    </tr>
    <!-- Champions League block -->
    <tr>
      <td class="hauptlink">
        <a href="/wettbewerb/CLQPA">UEFA Champions League</a>
      </td>
    </tr>
    <tr>
      <td>GS1</td>
      <td>Di 17.09.25</td>
      <td>FC Bayern München</td>
      <td>-</td>
      <td>GNK Dinamo Zagreb</td>
      <td>9:2</td>
      <td></td>
    </tr>
    <!-- DFB-Pokal block -->
    <tr>
      <td class="hauptlink">
        <a href="/wettbewerb/DFB">DFB-Pokal</a>
      </td>
    </tr>
    <tr>
      <td>R1</td>
      <td>So 26.10.25</td>
      <td>FC Bayern München</td>
      <td>-</td>
      <td>Alemannia Aachen</td>
      <td>4:0</td>
      <td></td>
    </tr>
    <!-- Unknown competition — should be filtered out -->
    <tr>
      <td class="hauptlink">
        <a href="/wettbewerb/SUPER">DFL-Supercup</a>
      </td>
    </tr>
    <tr>
      <td>-</td>
      <td>Sa 12.07.25</td>
      <td>FC Bayern München</td>
      <td>-</td>
      <td>Borussia Dortmund</td>
      <td>3:2</td>
      <td></td>
    </tr>
  </tbody>
</table>
</body>
</html>
"""

FUTURE_HTML = """\
<!DOCTYPE html>
<html>
<body>
<table class="spielplandaten">
  <tbody>
    <tr>
      <td class="hauptlink">
        <a href="/wettbewerb/L1">1. Bundesliga</a>
      </td>
    </tr>
    <tr>
      <td>18</td>
      <td>Sa 17.01.26</td>
      <td>FC Bayern München</td>
      <td>-</td>
      <td>1. FC Köln</td>
      <td>-:-</td>
      <td></td>
    </tr>
  </tbody>
</table>
</body>
</html>
"""


class TestMatchCatalogueSlugHelper:
    def test_slug_format(self):
        slug = match_catalogue._slug("2025-08-23", "Werder Bremen", "FC Bayern München")
        # ü → ue, space → hyphen
        assert slug == "2025-08-23_werder-bremen_fc-bayern-muenchen"

    def test_slug_lowercases_and_strips_special_chars(self):
        slug = match_catalogue._slug("2025-09-14", "Bayer 04 Leverkusen", "FC Bayern München")
        assert slug == "2025-09-14_bayer-04-leverkusen_fc-bayern-muenchen"

    def test_slug_collapses_multiple_separators(self):
        slug = match_catalogue._slug("2025-01-01", "A  B", "C  D")
        # Multiple spaces → single hyphen
        assert "--" not in slug


class TestMatchCatalogueScoreParsing:
    def test_parses_normal_score(self):
        h, a = match_catalogue._parse_score("3:1")
        assert h == 3 and a == 1

    def test_parses_score_with_spaces(self):
        h, a = match_catalogue._parse_score("2 : 0")
        assert h == 2 and a == 0

    def test_returns_none_for_future_match(self):
        h, a = match_catalogue._parse_score("-:-")
        assert h is None and a is None

    def test_returns_none_for_empty(self):
        h, a = match_catalogue._parse_score("")
        assert h is None and a is None

    def test_high_score(self):
        h, a = match_catalogue._parse_score("9:2")
        assert h == 9 and a == 2


class TestMatchCatalogueFetch:
    @respx.mock
    def test_parses_bundesliga_match(self, analysis_db: Path):
        respx.get(match_catalogue.TRANSFERMARKT_URL).mock(
            return_value=Response(200, html=FIXTURE_HTML)
        )
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            matches = match_catalogue.fetch_and_store()

        bl = [m for m in matches if m["competition"] == "Bundesliga"]
        assert len(bl) == 2

    @respx.mock
    def test_parses_champions_league_match(self, analysis_db: Path):
        respx.get(match_catalogue.TRANSFERMARKT_URL).mock(
            return_value=Response(200, html=FIXTURE_HTML)
        )
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            matches = match_catalogue.fetch_and_store()

        cl = [m for m in matches if m["competition"] == "Champions League"]
        assert len(cl) == 1
        assert cl[0]["home_goals"] == 9
        assert cl[0]["away_goals"] == 2

    @respx.mock
    def test_parses_dfb_pokal_match(self, analysis_db: Path):
        respx.get(match_catalogue.TRANSFERMARKT_URL).mock(
            return_value=Response(200, html=FIXTURE_HTML)
        )
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            matches = match_catalogue.fetch_and_store()

        dfb = [m for m in matches if m["competition"] == "DFB Pokal"]
        assert len(dfb) == 1

    @respx.mock
    def test_ignores_unknown_competitions(self, analysis_db: Path):
        respx.get(match_catalogue.TRANSFERMARKT_URL).mock(
            return_value=Response(200, html=FIXTURE_HTML)
        )
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            matches = match_catalogue.fetch_and_store()

        comps = {m["competition"] for m in matches}
        assert "DFL-Supercup" not in comps

    @respx.mock
    def test_total_match_count(self, analysis_db: Path):
        respx.get(match_catalogue.TRANSFERMARKT_URL).mock(
            return_value=Response(200, html=FIXTURE_HTML)
        )
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            matches = match_catalogue.fetch_and_store()

        assert len(matches) == 4  # 2 BL + 1 CL + 1 DFB, not the Supercup

    @respx.mock
    def test_matches_stored_in_db(self, analysis_db: Path):
        respx.get(match_catalogue.TRANSFERMARKT_URL).mock(
            return_value=Response(200, html=FIXTURE_HTML)
        )
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            match_catalogue.fetch_and_store()
            stored = db_module.list_matches()

        assert len(stored) == 4

    @respx.mock
    def test_future_match_no_score(self, analysis_db: Path):
        respx.get(match_catalogue.TRANSFERMARKT_URL).mock(
            return_value=Response(200, html=FUTURE_HTML)
        )
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            matches = match_catalogue.fetch_and_store()

        assert len(matches) == 1
        assert matches[0]["home_goals"] is None
        assert matches[0]["away_goals"] is None

    @respx.mock
    def test_iso_date_format(self, analysis_db: Path):
        respx.get(match_catalogue.TRANSFERMARKT_URL).mock(
            return_value=Response(200, html=FIXTURE_HTML)
        )
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            matches = match_catalogue.fetch_and_store()

        for m in matches:
            # All dates must be YYYY-MM-DD
            parts = m["date"].split("-")
            assert len(parts) == 3
            assert len(parts[0]) == 4  # year

    @respx.mock
    def test_fetch_and_store_is_idempotent(self, analysis_db: Path):
        respx.get(match_catalogue.TRANSFERMARKT_URL).mock(
            return_value=Response(200, html=FIXTURE_HTML)
        )
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            match_catalogue.fetch_and_store()
            match_catalogue.fetch_and_store()   # second call — no duplicates
            stored = db_module.list_matches()

        assert len(stored) == 4

    @respx.mock
    def test_http_error_raises(self, analysis_db: Path):
        respx.get(match_catalogue.TRANSFERMARKT_URL).mock(
            return_value=Response(503)
        )
        with patch.object(db_module, "ANALYSIS_DB_PATH", analysis_db):
            db_module.init_analysis_db()
            with pytest.raises(Exception):
                match_catalogue.fetch_and_store()
