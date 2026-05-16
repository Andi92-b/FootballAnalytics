from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.routers import player, profile, clusters
from backend import db as player_db

app = FastAPI(title="Football Analytics API", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    player_db.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(player.router)
app.include_router(profile.router)
app.include_router(clusters.router)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so CORS headers are always present on error responses."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
