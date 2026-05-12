---
name: "fetch-player"
description: "Fetches raw stats for one player via the three-tier pipeline: FBref (basic), Understat (xG/xA), WhoScored (advanced/stub). Returns a merged stats dict and a FetchResult with available_sources and data_freshness."
version: 0.2.0
capabilities:
  - "Tier A: FBref standard, shooting, misc tables via soccerdata (cached to .cache/fbref/)"
  - "Tier B: Understat npxG and xA for Big-5 leagues (cached to .cache/understat/)"
  - "Tier C: WhoScored advanced stats — stub in V1, returns None, pipeline degrades gracefully"
  - "Player row extraction with accent-insensitive matching"
  - "FetchResult with available_sources list and data_freshness dict"
triggers:
  - "fetch player"
  - "get stats for"
  - "scrape fbref"
  - "load player data"
  - "pull player stats"
  - "fetch fbref"
last_updated: 2026-05-12
---

# Fetch Player

Fetches and caches raw stats for one player across all three source tiers.

**Before executing:** Read `.claude/shared-references/fbref/table-guide.md` for the
current FBref data availability status.

---

## Step 1 — Clarify the request

Confirm with the operator:
1. Player name (accent-insensitive — "Luis Diaz" matches "Luis D\u00edaz")
2. League (soccerdata key, e.g. "ENG-Premier League")
3. Season start year (e.g. `2024` for 2024-25)

---

## Step 2 — Run the pipeline

Call `football_core.pipeline.fetch_all(league, season, cache_dir)`.

This runs three sub-steps:
1. **Tier A — FBref** (`sources/fbref.py`): fetches standard, shooting, misc tables. Caches to `.cache/fbref/<league>/<season>/`.
2. **Tier B — Understat** (`sources/understat.py`): fetches league-wide npxG/xA JSON. Big-5 only. Caches to `.cache/understat/<league_slug>/<season>.json`. Returns `None` for INT leagues.
3. **Tier C — WhoScored** (`sources/whoscored.py`): **stub in V1** — always returns `None`. Logs "Tier C unavailable".

The pipeline returns a `FetchResult` even if Tier B or C fails.

---

## Step 3 — Merge sources for the target player

Call `football_core.fetcher.merge_player_stats(name, tables)` to get the FBref flat dict.
Then call `football_core.sources.merger.merge_sources(stats, name, understat_data, whoscored_data)`
to inject `understat.*` and `whoscored.*` namespaced keys.

---

## Step 4 — Output verification JSON

Print a compact JSON summary: player name, available_sources, minutes, key metric inputs
(understat.npxG, understat.xA, misc.Performance_Int, etc.).


# Fetch Player

Fetches and caches raw FBref stats for one player across all required tables.

**Before executing:** Read `.claude/shared-references/fbref/table-guide.md` and
`.claude/shared-references/fbref/soccerdata-recipes.md`.

---

## Step 1 — Clarify the request

Confirm with the operator:
1. Player name (as it appears on FBref, e.g. "Virgil van Dijk")
2. League (e.g. "ENG-Premier League")
3. Season start year (e.g. `2024` for 2024-25)

---

## Step 2 — Check cache

For each of the 8 tables, check if `.cache/fbref/<league>/<season>/<table>.json` exists.
List which tables are cached and which need scraping.

---

## Step 3 — Scrape missing tables via soccerdata

Call `football_core.fetcher.fetch_tables(league, season, tables)` for any uncached tables.
Use recipes from `soccerdata-recipes.md`.

---

## Step 4 — Write cache

Save each scraped DataFrame as JSON to `.cache/fbref/<league>/<season>/<table>.json`.

---

## Step 5 — Extract player row

Filter the league-wide DataFrames to the target player by name.
Handle multi-row players (e.g. mid-season transfers) by taking the row with most minutes.

---

## Step 6 — Output verification JSON

Print a compact JSON summary: player name, tables present, minutes played, league, season.
This is the input to `compute-percentiles`.
