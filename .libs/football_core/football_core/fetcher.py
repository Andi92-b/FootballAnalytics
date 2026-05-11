"""
fetcher.py — soccerdata scrape + JSON cache read/write.

Public functions:
  fetch_tables(league, season, tables, cache_dir) -> dict[str, pd.DataFrame]
      Fetches (or loads from cache) each named stat table for the given league/season.
      Writes new scrapes to cache_dir/<league>/<season>/<table>.json.
      Returns a dict keyed by table name.

  get_player_row(df, player_name) -> pd.Series | None
      Extracts a single player row from a league-wide DataFrame.
      If multiple rows exist (transfer), returns the row with the most minutes.

  merge_player_stats(player_name, tables) -> dict
      Merges per-table player rows into a flat dict keyed by "<table>.<column>".

See .claude/shared-references/fbref/soccerdata-recipes.md for canonical implementation patterns.
"""

# Implementation: use soccerdata.FBref; follow recipes in soccerdata-recipes.md exactly.
# Column flattening, cache read/write, rate-limit sleep(4) between scrapes.
