---
name: "fetch-player"
description: "Fetches raw FBref stats for one player and season across all 8 required stat tables using the soccerdata library. Caches each table as JSON under .cache/fbref/. Returns the player's row(s) from each table as a merged dict."
version: 0.1.0
capabilities:
  - "Raw stats for one player across: standard, shooting, passing, passing_types, defense, possession, misc, team_stats"
  - "JSON cache written to .cache/fbref/<league>/<season>/<table>.json"
  - "Cache-hit detection — skips re-scrape when fresh cache exists"
  - "Player row extraction from league-wide DataFrame by player name"
  - "team_stats row fetched for possession-adjustment of defensive metrics"
triggers:
  - "fetch player"
  - "get stats for"
  - "scrape fbref"
  - "load player data"
  - "pull player stats"
  - "fetch fbref"
last_updated: 2026-05-11
---

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
