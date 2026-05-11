---
name: "compute-percentiles"
description: "Takes a player's raw stat rows (from fetch-player) and computes metric values and percentile ranks (0–99) within the positional peer group (same league, same position bucket, minimum 900 minutes played). Returns structured JSON."
version: 0.1.0
capabilities:
  - "Metric value computation for all metrics in the player's position profile using formulae from metric-definitions.md"
  - "Positional peer group filtering: same position bucket, 900+ minutes"
  - "Percentile rank calculation via scipy.stats.percentileofscore (kind='rank')"
  - "Structured output: { player, position, season, league, metrics: [{ name, category, raw, percentile }] }"
triggers:
  - "compute percentiles"
  - "calculate percentiles"
  - "rank player"
  - "percentile scores"
  - "build pizza data"
  - "percentile ranks"
last_updated: 2026-05-11
---

# Compute Percentiles

Computes metric values and percentile ranks for a player within their positional peer group.

**Before executing:** Read `.claude/shared-references/metrics/metric-definitions.md`.

---

## Step 1 — Load raw data

Accept the player row dict + full league DataFrames (output of `fetch-player`).

---

## Step 2 — Determine position bucket

Call `football_core.percentiles.map_position(fbref_pos_string)` to get the position bucket.
Then call the `position-profile` skill (or `football_core.metrics.get_profile`) to get the
ordered metric list for this position.

---

## Step 3 — Filter positional peer group

From the full league DataFrames, select all players with:
- Same position bucket (via `map_position`)
- Minimum 900 minutes played

---

## Step 4 — Compute metric raw values

For the player and every peer, compute all metric values in the position profile.
Apply possession-adjustment to defensive metrics using team_stats possession %.
Formulae come from `metric-definitions.md` — do not deviate.

---

## Step 5 — Compute percentile ranks

For each metric, call `scipy.stats.percentileofscore(peer_values, player_value, kind='rank')`.
Round to nearest integer. Clamp to 0–99.

---

## Step 6 — Output structured JSON

Return and print:
```json
{
  "player": "Virgil van Dijk",
  "position": "CB",
  "season": "2024-25",
  "league": "ENG-Premier League",
  "metrics": [
    { "name": "Front-foot defending", "category": "Defence", "raw": 4.21, "percentile": 78 }
  ]
}
```
This JSON is the input to `render-pizza` and `player-endpoint`.
