# soccerdata Recipes

Canonical Python snippets for fetching each of the 8 required FBref tables using the
`soccerdata` library. Use these as the starting point for `football_core/fetcher.py`.

**Import pattern:**
```python
import soccerdata as sd
import pandas as pd
import json
from pathlib import Path
```

---

## Initialising the FBref scraper

```python
fbref = sd.FBref(leagues="ENG-Premier League", seasons=2024)
```

- `leagues`: string or list of strings — use the soccerdata league ID
- `seasons`: int (start year) or list of ints

To suppress HTTP log noise in production:
```python
import logging
logging.getLogger("soccerdata").setLevel(logging.WARNING)
```

---

## Recipe 1: Standard stats

```python
df_standard = fbref.read_player_season_stats(stat_type="standard")
# Flatten MultiIndex columns if present
if isinstance(df_standard.columns, pd.MultiIndex):
    df_standard.columns = ['_'.join(col).strip('_') for col in df_standard.columns]
```

Key columns used: `Gls`, `Ast`, `npxG`, `xAG`, `PK`, `Min`, `Pos`, `Squad`

---

## Recipe 2: Shooting

```python
df_shooting = fbref.read_player_season_stats(stat_type="shooting")
if isinstance(df_shooting.columns, pd.MultiIndex):
    df_shooting.columns = ['_'.join(col).strip('_') for col in df_shooting.columns]
```

Key columns used: `Sh`, `npxG`, `npxG/Sh`

---

## Recipe 3: Passing

```python
df_passing = fbref.read_player_season_stats(stat_type="passing")
if isinstance(df_passing.columns, pd.MultiIndex):
    df_passing.columns = ['_'.join(col).strip('_') for col in df_passing.columns]
```

Key columns used: `Total_Att`, `Total_Cmp%`, `Short_Att`, `Med_Att`, `Long_Att`, `Prog`, `xAG`, `Ast`

---

## Recipe 4: Pass types

```python
df_passing_types = fbref.read_player_season_stats(stat_type="passing_types")
if isinstance(df_passing_types.columns, pd.MultiIndex):
    df_passing_types.columns = ['_'.join(col).strip('_') for col in df_passing_types.columns]
```

Key columns used: `Crs`

---

## Recipe 5: Defensive actions

```python
df_defense = fbref.read_player_season_stats(stat_type="defense")
if isinstance(df_defense.columns, pd.MultiIndex):
    df_defense.columns = ['_'.join(col).strip('_') for col in df_defense.columns]
```

Key columns used: `Tkl`, `Challenges_Att`, `Challenges_Tkl%`, `Blocks_Sh`, `Blocks_Pass`, `Int`, `Clr`

---

## Recipe 6: Possession

```python
df_possession = fbref.read_player_season_stats(stat_type="possession")
if isinstance(df_possession.columns, pd.MultiIndex):
    df_possession.columns = ['_'.join(col).strip('_') for col in df_possession.columns]
```

Key columns used: `Touches`, `Touches_Def3rd`, `Touches_Mid3rd`, `Touches_Att3rd`, `Touches_AttPen`,
`Dribbles_Att` (or `Take-Ons_Att`), `Carries`, `Carries_PrgC`, `Receiving_Rec`, `Receiving_PrgR`

---

## Recipe 7: Miscellaneous

```python
df_misc = fbref.read_player_season_stats(stat_type="misc")
if isinstance(df_misc.columns, pd.MultiIndex):
    df_misc.columns = ['_'.join(col).strip('_') for col in df_misc.columns]
```

Key columns used: `Fls`, `Aerial_Won`, `Aerial_Lost`, `Aerial_Won%`, `Recov`

---

## Recipe 8: Team possession %

FBref does not expose team stats through the per-player soccerdata reader directly. Use this
approach to derive team possession from the standard stats DataFrame:

```python
# After loading df_standard:
team_poss = (
    df_standard.groupby("Squad")["Poss"]
    .mean()                        # average across all players on the squad
    .div(100)                      # convert % to decimal
    .rename("team_poss")
    .reset_index()
)
# Then merge into the player DataFrame:
df_standard = df_standard.merge(team_poss, on="Squad", how="left")
```

If `Poss` is not present in the standard stats (some season/league combos), fall back to:
```python
# Default 50% possession if not available
df_standard["team_poss"] = df_standard.get("Poss", pd.Series(50, index=df_standard.index)) / 100
```

---

## Caching pattern

Cache each table as a JSON file keyed by league + season + table name:

```python
def cache_path(cache_dir: Path, league: str, season: int, table: str) -> Path:
    safe_league = league.replace(" ", "_").replace("-", "_")
    return cache_dir / safe_league / str(season) / f"{table}.json"

def save_cache(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(path, orient="records", date_format="iso")

def load_cache(path: Path) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_json(path, orient="records")
    return None
```

---

## Joining tables for a single player

After loading all tables, extract the player's row and merge into a flat dict:

```python
def get_player_row(df: pd.DataFrame, player_name: str) -> pd.Series | None:
    """Return the row with most minutes if multiple rows exist (e.g. transfers)."""
    mask = df["Player"] == player_name
    rows = df[mask]
    if rows.empty:
        return None
    if len(rows) > 1:
        # Handle mid-season transfers: take the row with most minutes
        min_col = next((c for c in ["Min", "Playing_Time_Min"] if c in rows.columns), None)
        if min_col:
            rows = rows.copy()
            rows[min_col] = rows[min_col].astype(str).str.replace(",", "").astype(float)
            return rows.loc[rows[min_col].idxmax()]
    return rows.iloc[0]
```

Merge all per-table rows into a single flat dict keyed by `<table>.<column>`:

```python
def merge_player_stats(player_name: str, tables: dict[str, pd.DataFrame]) -> dict:
    """tables: { "standard": df_standard, "shooting": df_shooting, ... }"""
    merged = {}
    for table_name, df in tables.items():
        row = get_player_row(df, player_name)
        if row is not None:
            for col, val in row.items():
                merged[f"{table_name}.{col}"] = val
    return merged
```

---

## Notes on rate limiting

FBref blocks scraping if requests come too fast. soccerdata includes built-in delays,
but when scraping many tables in sequence, add an explicit sleep:

```python
import time
TABLES = ["standard", "shooting", "passing", "passing_types", "defense", "possession", "misc"]
for table in TABLES:
    if not cache_path(cache_dir, league, season, table).exists():
        df = fbref.read_player_season_stats(stat_type=table)
        save_cache(df, cache_path(cache_dir, league, season, table))
        time.sleep(4)  # respect FBref rate limit
```
