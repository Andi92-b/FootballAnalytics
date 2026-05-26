"""
Minimal FastAPI entrypoint — analysis routes only.
Skips player/pizza/cluster routers that depend on football_core / soccerdata.
Use this in environments where soccerdata's GUI deps aren't available.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.routers import analysis
from backend import db as player_db

app = FastAPI(title="Football Analytics — Analysis API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup() -> None:
    player_db.init_analysis_db()

app.include_router(analysis.router)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
