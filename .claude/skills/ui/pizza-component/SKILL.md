---
name: "pizza-component"
description: "Writes the detailed React component specification for PizzaChart.tsx: TypeScript props interface, data shape expected from the API, visual behaviour for all states, and accessibility requirements. Does NOT implement the component — that is Claude Design's job via the design-handoff skill."
version: 0.1.0
capabilities:
  - "TypeScript props interface for PizzaChart component, exported as PizzaChartProps"
  - "Data shape documentation (mirrors the /api/player/{name} JSON response)"
  - "Visual behaviour specification for: loading, error, and data-loaded states"
  - "Accessibility requirements: aria-labels, role attributes, keyboard navigation"
  - "Output written to frontend/component-spec.md"
triggers:
  - "pizza component spec"
  - "component specification"
  - "spec the component"
  - "react component spec"
  - "component contract"
last_updated: 2026-05-11
---

# Pizza Component

Writes the detailed specification for the `PizzaChart` React component.
Output feeds directly into the `design-handoff` skill.

---

## Step 1 — Define TypeScript props interface

Write `PizzaChartProps` with:
- `svg: string` — raw SVG string from the API (primary render path)
- `player: string`, `position: string`, `season: string`, `league: string`
- `metrics: MetricResult[]` — array of `{ name, category, raw, percentile }`
- `isLoading: boolean`
- `error: string | null`

---

## Step 2 — Document data shape from API

Show the exact JSON shape returned by `GET /api/player/{name}` and map each field to a prop.

---

## Step 3 — Specify visual states

- **Loading:** spinner or skeleton centred in the chart area
- **Error:** friendly message with the error string, retry hint
- **Empty:** prompt: "Search for a player above"
- **Data:** render the SVG string directly via `dangerouslySetInnerHTML` or a React wrapper

---

## Step 4 — Specify accessibility requirements

- Chart container: `role="img"` with `aria-label="{player} pizza chart"`
- Metric list below chart for screen-reader users: `role="list"` with each metric as `role="listitem"`
- Loading state: `aria-live="polite"` region

---

## Step 5 — Output component-spec.md

Write the spec to `frontend/component-spec.md`.
This file travels to the `design-handoff` skill as input.
