---
name: "player-endpoint"
description: "Implements FastAPI GET /api/player/{name}. Orchestrates three-tier pipeline via data_service and returns enriched JSON including data_sources, missing_metrics, and data_freshness."
version: 0.2.0
capabilities:
  - "FastAPI GET route at /api/player/{name} in backend/app/routers/player.py"
  - "Query params: season (int), league (str)"
  - "Response: { player, position, season, league, data_sources[], missing_metrics[], data_freshness{}, metrics[{name,raw,percentile,source}], svg }"
  - "HTTP 404 if player not found; 422 if season unavailable"
  - "CORS headers on all responses including errors"
triggers:
  - "create endpoint"
  - "add api route"
  - "player endpoint"
  - "wire backend"
  - "expose api"
  - "fastapi route"
last_updated: 2026-05-12
---

# Player Endpoint

## Response schema (v0.2)

```json
{
  "player": "Luis D\u00edaz",
  "position": "CF",
  "season": "2024-25",
  "league": "ENG-Premier League",
  "data_sources": ["fbref", "understat"],
  "missing_metrics": ["Aerial volume", "Ball retention", "Loose ball recoveries", ...],
  "data_freshness": { "fbref": "2026-05-12", "understat": "2026-05-12" },
  "metrics": [
    { "name": "Goal threat", "category": "Attack", "raw": 0.47, "percentile": 99, "source": "A+B" },
    { "name": "Creative threat", "category": "Progression", "raw": 0.22, "percentile": 99, "source": "A+B" },
    { "name": "Shot quality", "category": "Attack", "raw": 0.17, "percentile": 99, "source": "A+B" }
  ],
  "svg": "<svg ...>"
}
```

## Implementation

1. `data_service.get_pizza_data()` calls `pipeline.fetch_all()` then `merge_sources()` for each player.
2. `compute_percentiles()` filters metrics by `available_sources`.
3. `chart_service.render()` generates SVG for computable metrics only.
4. `PlayerResponse` model mirrors the schema above.


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
