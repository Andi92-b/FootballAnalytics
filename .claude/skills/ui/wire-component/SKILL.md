---
name: "wire-component"
description: "Receives the designed PizzaChart React component from Claude Design and wires it to the live /api/player/{name} endpoint. Adds data fetching, PlayerSearch input, loading/error states, and integrates everything into the Next.js page. Fires at GATE: WIRE."
version: 0.1.0
capabilities:
  - "usePizzaData hook that calls GET /api/player/{name} with season and league params"
  - "PlayerSearch input component that triggers the API call on submit"
  - "PizzaChart component receives live API data through the hook"
  - "Loading spinner and error message states wired to the hook state"
  - "End-to-end flow: type name → submit → see pizza chart"
triggers:
  - "wire component"
  - "connect frontend"
  - "integrate design"
  - "GATE: WIRE"
  - "hook up api"
  - "connect to backend"
last_updated: 2026-05-11
---

# Wire Component

Connects the Claude Design–produced `PizzaChart` component to the live API.
This skill fires at **GATE: WIRE**, after Claude Design has returned the component file(s).

---

## Step 1 — Review received component interface

Read the returned `PizzaChart.tsx` (or equivalent files) from Claude Design.
Confirm the component accepts `PizzaChartProps` as specified in `design-spec.md`.
Note any deviations and resolve before continuing.

---

## Step 2 — Write usePizzaData hook

Create `frontend/src/hooks/usePizzaData.ts`:
- Accepts `{ name, season, league }` params
- Calls `GET /api/player/{name}?season=...&league=...` via `fetch`
- Returns `{ data, isLoading, error }`

---

## Step 3 — Write PlayerSearch input component

Create `frontend/src/components/PlayerSearch.tsx`:
- Text input + submit button
- On submit, calls the parent's `onSearch(name)` callback
- Shows a spinner while `isLoading` is true

---

## Step 4 — Wire PizzaChart into page.tsx

In `frontend/src/app/page.tsx`:
- Manage `playerName` state
- Call `usePizzaData` when `playerName` changes
- Render `<PlayerSearch>` and `<PizzaChart>` with live data

---

## Step 5 — Add loading and error states

Pass `isLoading` and `error` from the hook to `PizzaChart` props.
Confirm the component renders correctly for all three states (loading, error, data).

---

## Step 6 — Test end-to-end

Run `uvicorn` (backend) and `next dev` (frontend) concurrently.
Type a player name, confirm the pizza chart appears.
Declare **GATE: SHIP** passed when confirmed.
