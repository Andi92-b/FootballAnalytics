---
name: "position-profile"
description: "Maps an FBref position string (e.g. 'CB', 'RB', 'CM') to a position bucket and returns the ordered, category-grouped list of metrics to display for that position, per the position matrix."
version: 0.1.0
capabilities:
  - "FBref position string → position bucket (CB | FB | DM | CM | AM | W | CF)"
  - "Ordered metric list for the position bucket (✓ and ~ metrics only)"
  - "Category grouping: Defence → Possession → Progression → Attack (clockwise)"
  - "Returns a profile object suitable for passing to compute-percentiles and render-pizza"
triggers:
  - "position profile"
  - "which metrics for"
  - "metric subset"
  - "map position"
  - "position mapping"
last_updated: 2026-05-11
---

# Position Profile

Maps a raw FBref position string to an ordered, category-grouped metric list for chart rendering.

**Before executing:** Read `.claude/shared-references/metrics/position-matrix.md`.

---

## Step 1 — Map FBref string to position bucket

Use the mapping table in `position-matrix.md`:
- CB → `CB`
- RB, LB, RWB, LWB → `FB`
- DM → `DM`
- CM, MF → `CM`
- AM → `AM`
- RW, LW, LM, RM → `W`
- CF, FW, ST → `CF`

If the string is not in the map, ask the operator.

---

## Step 2 — Select metrics for position bucket

From the position matrix, collect all metrics where the bucket column is ✓ or ~.

---

## Step 3 — Order by category (D → P → Pr → A)

Sort selected metrics into category order:
1. Defence
2. Possession
3. Progression
4. Attack

Within each category, preserve the order from `metric-definitions.md`.

---

## Step 4 — Return profile object

Return:
```json
{
  "position_bucket": "CB",
  "fbref_string": "CB",
  "metrics": [
    { "name": "Front-foot defending", "category": "Defence" },
    { "name": "Tackle success",        "category": "Defence" }
  ]
}
```
