---
name: "player-endpoint"
description: "Implements the FastAPI route GET /api/player/{name}?season=2024&league=Premier+League. Orchestrates fetch-player → compute-percentiles → render-pizza and returns { player, position, season, league, metrics, svg }."
version: 0.1.0
capabilities:
  - "FastAPI GET route at /api/player/{name} in backend/app/routers/player.py"
  - "Query parameter validation: season (int, default current), league (str, default ENG-Premier League)"
  - "Calls football_core services in sequence: data_service then chart_service"
  - "JSON response: { player, position, season, league, metrics[], svg }"
  - "HTTP 404 if player not found in the league data; HTTP 422 on invalid params"
  - "CORS headers configured so the Next.js dev server can call the API"
triggers:
  - "create endpoint"
  - "add api route"
  - "player endpoint"
  - "wire backend"
  - "expose api"
  - "fastapi route"
last_updated: 2026-05-11
---

# Player Endpoint

Implements the `GET /api/player/{name}` FastAPI route that orchestrates the full data → chart pipeline.

---

## Step 1 — Write route handler skeleton

In `backend/app/routers/player.py`:
- `router = APIRouter(prefix="/api")`
- `@router.get("/player/{name}")` with `season: int` and `league: str` query params

---

## Step 2 — Add query parameter defaults and validation

Default `season` to the current year. Default `league` to `"ENG-Premier League"`.
Add a `PlayerResponse` Pydantic model that matches the JSON shape.

---

## Step 3 — Wire service calls

`data_service.get_pizza_data(name, season, league)` → calls `fetch_player` + `compute_percentiles`.
`chart_service.render(pizza_data)` → calls `render_pizza`.

---

## Step 4 — Add error handling

Raise `HTTPException(404)` if the player is not found.
Let FastAPI handle `RequestValidationError` (422) automatically.

---

## Step 5 — Register router in main.py

`app.include_router(player.router)` in `backend/app/main.py`.
Add CORS middleware allowing `http://localhost:3000`.

---

## Step 6 — Verify with curl

Run the dev server with `uvicorn backend.app.main:app --reload` and execute:
```bash
curl "http://localhost:8000/api/player/Virgil%20van%20Dijk?season=2024&league=ENG-Premier+League"
```
Confirm response contains `player`, `position`, `metrics[]`, and `svg` fields.
