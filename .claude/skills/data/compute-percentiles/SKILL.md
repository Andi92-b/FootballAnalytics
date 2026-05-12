---
name: "compute-percentiles"
description: "Takes a player's merged stats dict (from fetch-player, all three tiers merged) and computes percentile ranks for the metrics available given the active source tiers. Returns MetricResult list + missing_metrics list."
version: 0.2.0
capabilities:
  - "Filters the position profile to only metrics computable from available_sources"
  - "Metrics in PENDING_METRICS or requiring unavailable tiers → missing_metrics list"
  - "Percentile rank via scipy.stats.percentileofscore (kind='rank'), clamped 0–99"
  - "Each MetricResult includes a 'source' field (e.g. 'A', 'A+B', 'C', 'pending')"
  - "Returns (list[MetricResult], list[str]) — results + missing_metrics"
triggers:
  - "compute percentiles"
  - "calculate percentiles"
  - "rank player"
  - "percentile scores"
  - "build pizza data"
  - "percentile ranks"
last_updated: 2026-05-12
---

# Compute Percentiles

Computes metric values and percentile ranks for a player, respecting available source tiers.

**Before executing:** Read `.claude/shared-references/metrics/metric-definitions.md`.

---

## Step 1 — Load merged stats

Accept the player merged dict from `fetch-player` (with `understat.*` and `whoscored.*` keys).

---

## Step 2 — Determine position bucket and metric list

Call `map_position()`. Get the full position profile. Then filter:
- If metric name is in `PENDING_METRICS` → `missing_metrics`
- If tier is `A+B` and `"understat"` not in `available_sources` → `missing_metrics`
- If tier is `C` or `A+C` and `"whoscored"` not in `available_sources` → `missing_metrics`

---

## Step 3 — Filter peer group and compute percentiles

For computable metrics only: build peer group (same position bucket, 900+ min), compute raw values for all peers, then `percentileofscore`.

---

## Step 4 — Output structured JSON

```json
{
  "player": "Luis D\u00edaz",
  "position": "CF",
  "data_sources": ["fbref", "understat"],
  "metrics": [
    { "name": "Goal threat", "category": "Attack", "raw": 0.47, "percentile": 99, "source": "A+B" }
  ],
  "missing_metrics": ["Aerial volume", "Aerial success", "Loose ball recoveries", ...]
}
```


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
