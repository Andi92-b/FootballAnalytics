"""
Analysis API router — match catalogue, text fetch, LLM extraction, pattern report.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend import db
from backend.app.services import (
    match_catalogue,
    pattern_analyzer,
    text_fetcher,
    llm_extractor,
)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


# ── Match catalogue ───────────────────────────────────────────────────────────

@router.get("/matches")
def list_matches(competition: str | None = None) -> list[dict]:
    return db.list_matches(competition=competition)


@router.post("/matches/refresh")
def refresh_matches() -> dict:
    """Scrape Transfermarkt and upsert all Bayern 2025-26 matches."""
    matches = match_catalogue.fetch_and_store()
    return {"upserted": len(matches)}


# ── Match detail ──────────────────────────────────────────────────────────────

@router.get("/match/{match_id}")
def get_match(match_id: str) -> dict:
    match = db.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return {
        "match": match,
        "events": db.get_match_events(match_id),
        "shots": db.get_match_shots(match_id),
        "sources": [
            {k: v for k, v in s.items() if k != "content"}
            for s in db.get_text_sources(match_id)
        ],
    }


# ── Text fetch ────────────────────────────────────────────────────────────────

@router.post("/fetch/{match_id}")
def fetch_text(match_id: str) -> dict:
    match = db.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    results = text_fetcher.fetch_all_text(match)
    fetched = [src for src, content in results.items() if content]
    return {"match_id": match_id, "fetched_sources": fetched}


# ── LLM extraction ────────────────────────────────────────────────────────────

def _run_extraction(match_id: str) -> list[dict]:
    texts = db.get_text_sources(match_id)
    if not texts:
        return []
    return llm_extractor.extract_match_events(match_id, texts)


@router.post("/extract/{match_id}")
def extract_match(match_id: str) -> dict:
    match = db.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    events = _run_extraction(match_id)
    return {"match_id": match_id, "events_extracted": len(events)}


@router.post("/extract/all")
def extract_all(background_tasks: BackgroundTasks) -> dict:
    """Trigger LLM extraction for all unanalysed matches that have text sources."""
    matches = db.list_matches()
    pending = [m for m in matches if not m["analysed"]]

    def _run_all() -> None:
        for m in pending:
            texts = db.get_text_sources(m["id"])
            if texts:
                llm_extractor.extract_match_events(m["id"], texts)

    background_tasks.add_task(_run_all)
    return {"queued": len(pending)}


# ── Pattern report ────────────────────────────────────────────────────────────

@router.get("/patterns")
def get_patterns(competition: str | None = None) -> dict:
    report = pattern_analyzer.build_report(competition=competition)
    return report.model_dump()
