# FBref Table Guide

Reference for the `soccerdata` table names, corresponding FBref stat page URLs,
required columns, and known scraping quirks for each of the 8 tables used in
the pizza chart pipeline.

---

## ⚠️ DATA SOURCE CHANGE — 2026-01-20

**FBref terminated its Opta/Stats Perform data contract on 2026-01-20.**

The following tables are **no longer available** from FBref (pages exist but return no stat cells):
- `passing` — all pass split / progressive pass / xAG data gone
- `passing_types` — crosses, key passes, set piece types gone
- `defense` — tackles, challenges, blocks, clearances gone
- `possession` — touches by zone, carries, dribbles, progressive carries/receptions gone

The pipeline now uses a **three-tier strategy**:
- **Tier A — FBref** (`standard`, `shooting`, `misc`) — basic stats, still valid
- **Tier B — Understat** (`https://understat.com`) — npxG, xA (Big-5 leagues only)
- **Tier C — WhoScored** (stub in V1) — touches, carries, dribbles, advanced defensive stats

### What FBref still provides

| Table | Available columns |
|-------|-------------------|
| `standard` | Goals, Assists, PK, Minutes, Position (`Performance_*` prefix) |
| `shooting` | Shots (`Standard_Sh`), basic shot stats |
| `misc` | Yellow/red cards, Fouls committed (`Performance_Fls`), Interceptions (`Performance_Int`), Tackles won (`Performance_TklW`) |

### What moved to alternative sources

| Stat | Old source | New source |
|------|-----------|------------|
| npxG, xA | FBref shooting/passing | **Tier B: Understat** |
| Touches by zone, carries, dribbles | FBref possession | **Tier C: WhoScored (pending)** |
| Tackles, challenges, blocks | FBref defense | **Tier C: WhoScored (pending)** |
| Clearances, blocked shots | FBref defense | **Tier C: WhoScored (pending)** |
| Pass splits, xAG, progressive passes | FBref passing | **No open source — pending_data** |
| Pass completion % | FBref passing | **No open source — pending_data** |
| Progressive carries/receptions | FBref possession | **No open source — pending_data** |

---

## Quick-reference table

| soccerdata table key | FBref stat page URL path | soccerdata `stat` param | Status |
|---|---|---|---|
| Standard stats | `/en/comps/{id}/{season}/stats/` | `"standard"` | ✅ Available |
| Shooting | `/en/comps/{id}/{season}/shooting/` | `"shooting"` | ✅ Available (basic only) |
| Miscellaneous | `/en/comps/{id}/{season}/misc/` | `"misc"` | ✅ Available (basic only) |
| Passing | `/en/comps/{id}/{season}/passing/` | `"passing"` | ❌ Empty post-2026-01-20 |
| Pass types | `/en/comps/{id}/{season}/passing_types/` | `"passing_types"` | ❌ Empty post-2026-01-20 |
| Defensive actions | `/en/comps/{id}/{season}/defense/` | `"defense"` | ❌ Empty post-2026-01-20 |
| Possession | `/en/comps/{id}/{season}/possession/` | `"possession"` | ❌ Empty post-2026-01-20 |

---

## Per-table details

### `standard`

**FBref page:** Player Standard Stats  
**Required columns:**

| Column name on FBref | pandas column after soccerdata | Notes |
|---|---|---|
| `Gls` | `Goals` or `Gls` | Goals scored |
| `Ast` | `Assists` or `Ast` | Assists |
| `xG` | `xG` | Expected goals (total, includes pens) |
| `xAG` | `xAG` | Expected assists |
| `npxG` | `npxG` | Non-penalty xG |
| `PK` | `PK` | Penalty kicks scored |
| `Min` | `Min` or `Playing_Time_Min` | Minutes played — used for 900-min filter |
| `Pos` | `Pos` | Primary position string |

**Quirk:** The `Min` column may contain commas (e.g. `"1,890"`). Strip commas before casting to int.

---

### `shooting`

**FBref page:** Player Shooting  
**Required columns:**

| Column | pandas column | Notes |
|---|---|---|
| `Sh` | `Sh` or `Standard_Sh` | Total shots |
| `npxG` | `npxG` or `Expected_npxG` | Non-penalty xG from shooting table |
| `npxG/Sh` | `npxG/Sh` or `Expected_npxG/Sh` | xG per shot (pre-computed) |

**Quirk:** `npxG` appears in both `standard` and `shooting`. Use the `shooting` table value for
shot-specific metrics; they may differ slightly due to rounding. Prefer `shooting.npxG` for
`Goal threat` and `Shot quality`.

---

### `passing`

**FBref page:** Player Passing  
**Required columns:**

| Column | pandas column | Notes |
|---|---|---|
| `Total.Att` | `Total_Att` or `Att` | Total passes attempted |
| `Total.Cmp%` | `Total_Cmp%` or `Cmp%` | Pass completion % |
| `Short.Att` | `Short_Att` | Short passes attempted |
| `Med.Att` | `Medium_Att` or `Med_Att` | Medium passes attempted |
| `Long.Att` | `Long_Att` | Long passes attempted |
| `Prog` | `Prog` or `PrgP` | Progressive passes |
| `xAG` | `xAG` | Expected assisted goals (from passing table) |
| `Ast` | `Ast` | Actual assists — note: also in `standard` |

**Quirk:** Column names for pass distance groups vary by soccerdata version. May appear as
`Short_Att`, `Med_Att`, `Long_Att` or as a MultiIndex with levels `("Short", "Att")`.
Always inspect the DataFrame columns after scraping and normalise to flat names.

---

### `passing_types`

**FBref page:** Player Pass Types  
**Required columns:**

| Column | pandas column | Notes |
|---|---|---|
| `Crs` | `Crs` or `Pass_Types_Crs` | Crosses |

**Quirk:** This table has many columns; only `Crs` is required. Safe to drop all others after
selecting the player row.

---

### `defense`

**FBref page:** Player Defensive Actions  
**Required columns:**

| Column | pandas column | Notes |
|---|---|---|
| `Tkl` | `Tkl` or `Tackles_Tkl` | Tackles won |
| `Challenges.Att` | `Challenges_Att` | Dribbles challenged |
| `Challenges.Tkl%` | `Challenges_Tkl%` or `Tkl%` | Tackle success % |
| `Blocks.Sh` | `Blocks_Sh` | Shot blocks |
| `Blocks.Pass` | `Blocks_Pass` | Pass blocks |
| `Int` | `Int` | Interceptions |
| `Clr` | `Clr` | Clearances |

**Quirk:** MultiIndex columns are common here. After calling `reset_index()` or flattening,
`Challenges_Tkl%` may become `Tkl%` depending on version — confirm by inspecting columns.

---

### `possession`

**FBref page:** Player Possession  
**Required columns:**

| Column | pandas column | Notes |
|---|---|---|
| `Touches` | `Touches` or `Touches_Touches` | Total touches |
| `Touches.Def3rd` | `Touches_Def3rd` | Touches in own defensive third |
| `Touches.Mid3rd` | `Touches_Mid3rd` | Touches in middle third |
| `Touches.Att3rd` | `Touches_Att3rd` | Touches in attacking third |
| `Touches.AttPen` | `Touches_AttPen` | Touches in opponent penalty area |
| `Dribbles.Att` | `Dribbles_Att` or `Take-Ons_Att` | Dribbles / take-ons attempted |
| `Carries` | `Carries` or `Carries_Carries` | Total carries |
| `PrgC` | `PrgC` or `Carries_PrgC` | Progressive carries |
| `Receiving.Rec` | `Receiving_Rec` | Passes received |
| `Receiving.PrgR` | `Receiving_PrgR` | Progressive passes received |

**Quirk:** FBref renamed "Dribbles" to "Take-Ons" in the 2022-23 season. soccerdata may
surface either name depending on the season. Check both `Dribbles_Att` and `Take-Ons_Att`.

---

### `misc`

**FBref page:** Player Miscellaneous Stats  
**Required columns:**

| Column | pandas column | Notes |
|---|---|---|
| `Fls` | `Fls` or `Performance_Fls` | Fouls committed |
| `Aerial.Won` | `Aerial_Won` or `Aerial Duels_Won` | Aerial duels won |
| `Aerial.Lost` | `Aerial_Lost` or `Aerial Duels_Lost` | Aerial duels lost |
| `Aerial.Won%` | `Aerial_Won%` or `Aerial Duels_Won%` | Aerial win % |
| `Recov` | `Recov` or `Performance_Recov` | Ball recoveries |

**Quirk:** `Aerial Won%` may be `NaN` for players with 0 aerial duels. Treat as 0 for
percentile purposes (do not drop the player from the peer group).

---

### Team stats (possession %)

**Required column:** `Poss` — team possession % (as integer, e.g. 55 for 55%)

**Approach:** soccerdata does not expose a clean `team_stats` table for player league data.
The recommended approach is:

1. After loading the `standard` table (which is league-wide), compute per-team `Poss` by
   taking the mean of all player `Poss` values grouped by `Squad`.
2. Alternatively, scrape the squad-level standard stats page which includes `Poss` directly.

Convert `Poss` to a decimal (0.55) before using in the possession-adjustment formula.

---

## General soccerdata quirks

1. **Rate limiting / scrape delays:** soccerdata respects FBref's scrape limits. Add `sleep(4)`
   between table requests or use soccerdata's built-in `no_cache=False` with a local disk cache.
2. **Season format:** soccerdata uses the season *start* year as an integer: `2024` = 2024-25.
3. **League IDs:** Use string league IDs, e.g. `"ENG-Premier League"`, `"ESP-La Liga"`.
   Full list: `soccerdata.FBref.available_leagues()`.
4. **Column flattening:** DataFrames returned by soccerdata often have MultiIndex columns.
   Call `df.columns = ['_'.join(col).strip('_') for col in df.columns]` to flatten safely.
5. **Player name matching:** Names may differ between tables (e.g. accents, abbreviations).
   Match on `Player` column using exact string first; fall back to fuzzy match via `difflib`.
