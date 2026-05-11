# Shared References — Index

This directory contains domain knowledge loaded on demand by skills.
Skills instruct you to read specific files before executing — do not load these proactively.

| File | Loaded by skill(s) | Contents |
|------|--------------------|----------|
| `metrics/metric-definitions.md` | `compute-percentiles`, `render-pizza` | All 17 metrics: definition, FBref table, formula, tactical meaning |
| `metrics/position-matrix.md` | `position-profile`, `compute-percentiles` | Position × metric matrix; FBref string → bucket mapping |
| `fbref/table-guide.md` | `fetch-player` | soccerdata table names, column quirks, scraping gotchas |
| `fbref/soccerdata-recipes.md` | `fetch-player` | Canonical Python snippets for all 8 required tables |
| `design/pizza-chart-visual-spec.md` | `render-pizza`, `design-handoff` | Slice order, colour palette, typography, PyPizza config |
| `design/claude-design-handoff-guide.md` | `design-handoff` | How to write design-spec.md for Claude Design |
