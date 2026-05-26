# Bayern München Playing Style Analysis — Full Season Dashboard

## Context

Build a playing style analysis system for FC Bayern München across all competitions in the
2025-26 season (Bundesliga, Champions League, DFB Pokal). The system combines quantitative
shot data from Understat with qualitative tactical context extracted from match reports and
live tickers (Kicker, SZ, UEFA.com) via the Claude API. Output: a web dashboard integrated
into the existing FastAPI/Next.js app showing offensive/defensive patterns, per-match
breakdowns, and supporting article quotes.

This replaces the earlier shot-map-only plan entirely.

---

## Architecture

```
Data sources                    Processing                  Storage (SQLite)
────────────────                ──────────────────          ────────────────
Understat (Bundesliga)    →     fetch_team_shots()    →     match_shots
Kicker ticker/report     →     scrape_kicker()       →     text_sources
SZ articles (user drop)  →     load_sz_files()       →     text_sources
UEFA.com (CL)            →     scrape_uefa()         →     text_sources
Transfermarkt            →     fetch_match_list()    →     matches
                                      ↓
                          llm_extractor.py (Claude API)
                          — per match, extracts events
                                      ↓
                               match_events table
                                      ↓
                          pattern_analyzer.py (aggregate)
                                      ↓
                          FastAPI routers → Next.js dashboard
```

---

## Phase 1 — Data Foundation

### 1a. Database schema extension
**File:** `backend/db.py` — extend with 4 new tables alongside existing `players` tables.

```sql
CREATE TABLE IF NOT EXISTS matches (
    id          TEXT PRIMARY KEY,   -- "{date}_{home}_{away}" slug
    date        TEXT,
    competition TEXT,               -- "Bundesliga" | "Champions League" | "DFB Pokal"
    home_team   TEXT,
    away_team   TEXT,
    home_goals  INTEGER,
    away_goals  INTEGER,
    analysed    INTEGER DEFAULT 0   -- 1 when LLM extraction complete
);

CREATE TABLE IF NOT EXISTS match_shots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id    TEXT REFERENCES matches(id),
    x           REAL,  y REAL,
    xG          REAL,
    result      TEXT,  -- "Goal" | "SavedShot" | etc.
    situation   TEXT,  -- "OpenPlay" | "SetPiece" | "Penalty" | etc.
    shot_type   TEXT,  -- "RightFoot" | "LeftFoot" | "Head"
    minute      INTEGER,
    player      TEXT,
    team        TEXT   -- "Bayern" or opponent
);

CREATE TABLE IF NOT EXISTS text_sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id    TEXT REFERENCES matches(id),
    source      TEXT,  -- "kicker_ticker" | "kicker_report" | "sz" | "uefa"
    content     TEXT,
    fetched_at  TEXT
);

CREATE TABLE IF NOT EXISTS match_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id            TEXT REFERENCES matches(id),
    minute              INTEGER,
    type                TEXT,  -- see taxonomy below
    direction           TEXT,  -- "offensive" | "defensive"
    situation           TEXT,
    trigger             TEXT,
    defensive_cover     TEXT,
    players_involved    TEXT,  -- JSON array as text
    outcome             TEXT,
    description         TEXT,  -- quote from source article
    confidence          TEXT   -- "high" | "medium" | "low"
);
```

Add CRUD helpers to `db.py` following the existing `row_factory=sqlite3.Row` + `_conn()` pattern.

### 1b. Match catalogue service
**New file:** `backend/app/services/match_catalogue.py`

Scrapes Transfermarkt for all Bayern matches in 2025-26 across all competitions using
`httpx`. URL: `https://www.transfermarkt.de/fc-bayern-munchen/spielplan/verein/27/saison_id/2025`
(public, no auth needed). Parses date, competition, teams, score. Upserts into `matches` table.

Competitions to capture: filter for "1. Bundesliga", "UEFA Champions League", "DFB-Pokal".

### 1c. Dependencies
**File:** `backend/pyproject.toml` — add:
```
"anthropic>=0.40",
"httpx>=0.27",
"beautifulsoup4>=4.12",
```

**File:** `.env.example` — add `ANTHROPIC_API_KEY=sk-ant-...`

---

## Phase 2 — Text Data Collection

### 2a. Kicker scraper
**New file:** `backend/app/services/text_fetcher.py`

Two functions:
- `scrape_kicker_ticker(match: dict) -> str` — fetches Kicker live ticker page for the match.
  URL pattern: `https://www.kicker.de/fc-bayern-muenchen-gegen-{opponent}/liveticker/{competition}/{season}/{match-id}`
  (exact slug discovered from Transfermarkt match page or Google search at implementation time).
  Parses `<div class="timeline-entry">` blocks with minute + text content via BeautifulSoup.

- `scrape_kicker_report(match: dict) -> str` — fetches the "Spielbericht" (match report).
  Returns plain text of article body.

Both save to `text_sources` table with `source="kicker_ticker"` / `"kicker_report"`.

### 2b. SZ file loader
User drops manually downloaded SZ HTML files into `.cache/sz_articles/`.
Naming convention: `{match_id}.html` (e.g. `2025-11-02_bayer-leverkusen_fc-bayernmuenchen.html`).

`load_sz_files(match_id) -> str | None` — reads from `.cache/sz_articles/{match_id}*.html`,
extracts `<article>` body text via BeautifulSoup, saves to `text_sources` with `source="sz"`.

### 2c. UEFA.com scraper (CL matches only)
`scrape_uefa_report(match: dict) -> str` — fetches the UEFA match report from
`https://www.uefa.com/uefachampionsleague/match/{uefa_match_id}/`.
Match ID sourced from Transfermarkt external links field.

---

## Phase 3 — LLM Extraction

### 3a. Extractor service
**New file:** `backend/app/services/llm_extractor.py`

Uses `anthropic` Python SDK with `claude-sonnet-4-6` (**confirmed**; ~$2–3 for the full
~55-match season with prompt caching). Reads all `text_sources` rows for a match,
concatenates into a single prompt, extracts structured events.

**Prompt strategy:** System prompt (cacheable via `cache_control: {"type": "ephemeral"}`)
defines the taxonomy + output schema. User message contains the combined match text.
Response is a JSON object. Caching saves ~80% input-token cost on repeated runs.

**Event taxonomy:**
```
type:           goal | big_chance | chance_created | chance_conceded |
                pressing_success | pressing_failure | tactical_change | substitution
direction:      offensive | defensive
situation:      counterattack | buildup_play | set_piece_attack | set_piece_defense |
                individual_error | high_press | low_block_break | transition | penalty
trigger:        ball_loss_midfield | ball_loss_defensive | corner | free_kick |
                second_ball | individual_mistake | through_ball | cross | penalty_foul
defensive_cover: 1v1 | 2v1 | 2v2 | 3v2 | outnumbered | adequate | unclear
outcome:        goal | saved | missed | blocked | chance | no_chance
confidence:     high | medium | low
```

Function signature:
```python
def extract_match_events(match_id: str, texts: list[dict]) -> list[dict]:
    """Calls Claude API, returns list of event dicts. Marks match as analysed=1 on success."""
```

Enable prompt caching on the system prompt (saves ~80% token cost on repeated calls).

### 3b. Extraction CLI trigger
**New file:** `backend/scripts/run_extraction.py`

CLI script: `python -m backend.scripts.run_extraction --match-id all` or `--match-id {id}`.
Runs text fetch → LLM extraction for matches where `analysed=0`.
Also triggerable via `POST /api/analysis/extract` endpoint.

---

## Phase 4 — Pattern Analysis

### 4a. Pattern aggregation
**New file:** `backend/app/services/pattern_analyzer.py`

Reads `match_events` table, aggregates:
- Defensive patterns: group by `situation × trigger`, count frequency, list supporting quotes
- Offensive patterns: same for `direction="offensive"`
- Per-competition breakdown
- Score-state analysis (goals conceded when winning / drawing / losing)

Returns `PatternReport` Pydantic model.

---

## Phase 5 — API Layer

### 5a. New router
**New file:** `backend/app/routers/analysis.py`

```
GET  /api/analysis/matches              — list all matches with analysed status
GET  /api/analysis/match/{id}           — match detail: events + shots + sources
GET  /api/analysis/patterns             — aggregated pattern report
POST /api/analysis/fetch/{match_id}     — trigger text fetch for one match
POST /api/analysis/extract/{match_id}   — trigger LLM extraction for one match
POST /api/analysis/extract/all          — extract all unanalysed matches
```

**File:** `backend/app/main.py` — add `from backend.app.routers import ... analysis` and
`app.include_router(analysis.router)`.

---

## Phase 6 — Frontend Dashboard

Three new Next.js pages, all under `/analysis`:

### `/analysis` — Season overview
**New file:** `frontend/src/app/analysis/page.tsx`

- Match list table: date, competition, opponent, result, analysed status
- Filter tabs: All / Bundesliga / Champions League / DFB Pokal
- Summary stats: W/D/L, goals for/against, xG for/against (Bundesliga only), matches analysed

### `/analysis/patterns` — Pattern analysis
**New file:** `frontend/src/app/analysis/patterns/page.tsx`

- Toggle: Defensive / Offensive
- Bar chart: top situations by frequency (using existing Recharts or simple SVG)
- Pattern cards: each card shows situation label + frequency + top 3 supporting article quotes
- Pitch heatmap: shot locations coloured by situation (reuses shot map renderer from Phase 1
  of original plan, but filtered by situation type)
- Competition filter

### `/analysis/match/[id]` — Match detail
**New file:** `frontend/src/app/analysis/match/[id]/page.tsx`

- Match header: date, score, competition
- Event timeline: sorted by minute, each event as a card with type icon + description quote
- Shot scatter (Bundesliga only): inline SVG from backend
- "Fetch & Analyse" button if match not yet analysed

### Navigation
**File:** `frontend/src/app/page.tsx` — add "Bayern Analysis →" nav link alongside
existing "Cluster Explorer →" link.

---

## Files Modified / Created

| File | Action |
|---|---|
| `backend/db.py` | Add 4 tables + CRUD helpers |
| `backend/pyproject.toml` | Add anthropic, httpx, beautifulsoup4 |
| `.env.example` | Add ANTHROPIC_API_KEY |
| `backend/app/services/match_catalogue.py` | New — Transfermarkt scraper |
| `backend/app/services/text_fetcher.py` | New — Kicker + SZ + UEFA scrapers |
| `backend/app/services/llm_extractor.py` | New — Claude API extraction |
| `backend/app/services/pattern_analyzer.py` | New — pattern aggregation |
| `backend/app/routers/analysis.py` | New — analysis API endpoints |
| `backend/app/main.py` | Register analysis router |
| `backend/scripts/run_extraction.py` | New — CLI trigger for extraction |
| `frontend/src/app/analysis/page.tsx` | New — season overview |
| `frontend/src/app/analysis/patterns/page.tsx` | New — pattern dashboard |
| `frontend/src/app/analysis/match/[id]/page.tsx` | New — match detail |
| `frontend/src/app/page.tsx` | Add nav link |

Plus Understat shot map additions from original plan (models, renderer, shots router) remain
valid as the quantitative layer — implement alongside Phase 1.

---

## Execution Order

1. Phase 1 (DB schema + dependencies) — foundation for everything else
2. Phase 2a (Kicker scraper) — test on one match before scaling
3. Phase 3 (LLM extractor) — test on one match with Kicker text only
4. Phase 4 (patterns) — once ≥5 matches analysed
5. Phase 5 (API) — wires everything together
6. Phase 6 (frontend) — build incrementally: match list → match detail → patterns

Process **one match end-to-end** before running the full season batch.

---

## Verification

1. `python -m backend.scripts.run_extraction --match-id {one-match-id}`
   → check `.cache/` for text files + `match_events` rows in SQLite
2. `curl http://localhost:8000/api/analysis/match/{id}` → JSON with events + quotes
3. `curl http://localhost:8000/api/analysis/patterns` → pattern report with frequencies
4. Open `http://localhost:3000/analysis` → match list loads, filter works
5. Open `http://localhost:3000/analysis/patterns` → bar chart shows defensive situations
6. Spot-check 3 extracted events against source article text for accuracy
