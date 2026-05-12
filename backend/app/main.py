from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers import player

app = FastAPI(title="Football Analytics API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(player.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
