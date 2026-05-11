---
name: "render-pizza"
description: "Renders a position-specific pizza chart SVG string for one player using mplsoccer.PyPizza. Accepts the structured percentile JSON from compute-percentiles and returns an inline SVG string."
version: 0.1.0
capabilities:
  - "SVG string output for a player's pizza chart (no file written, returned as string)"
  - "Category colour-coding per pizza-chart-visual-spec.md"
  - "Clockwise slice order: Defence → Possession → Progression → Attack"
  - "Percentile value labels on each slice"
  - "Player name, position bucket, and season in the title block"
  - "Consistent with mplsoccer PyPizza API"
triggers:
  - "render pizza"
  - "draw chart"
  - "generate svg"
  - "create pizza chart"
  - "visualise player"
  - "pizza svg"
last_updated: 2026-05-11
---

# Render Pizza

Renders a position-specific pizza chart SVG for one player using `mplsoccer.PyPizza`.

**Before executing:** Read `.claude/shared-references/design/pizza-chart-visual-spec.md`.

---

## Step 1 — Accept percentile JSON input

Receive the structured dict from `compute-percentiles`:
`{ player, position, season, league, metrics: [{ name, category, raw, percentile }] }`.

---

## Step 2 — Extract slice values and labels

Extract ordered list of: metric names (labels), percentile values (slice fill %), categories.
Preserve D → P → Pr → A clockwise order from the metrics list.

---

## Step 3 — Configure PyPizza layout per visual spec

Set background colour, slice colours by category, straight-line or curved comparison line,
font sizes, label placement — all per `pizza-chart-visual-spec.md`.

---

## Step 4 — Render to SVG string

Use `matplotlib` with a `BytesIO` / SVG backend to capture the figure as an SVG string.
Do not write to disk.

---

## Step 5 — Return SVG string

Return the raw SVG string. Print the first 200 chars as verification.
This string is passed directly to the `player-endpoint` API response.
