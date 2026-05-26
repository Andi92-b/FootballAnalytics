"""
Analysis API router — match catalogue, text fetch, LLM extraction, pattern report.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend import db
from backend.app.services import (
    match_catalogue,
    match_data_fetcher,
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
def refresh_matches(season: int = 2025, force: bool = False) -> dict:
    """
    Refresh the match catalogue from all available sources.

    Sources tried (in order of reliability):
      1. Understat team endpoint  — Bundesliga results + xG (cloud-friendly)
      2. FBref read_schedule()    — schedule + match xG (requires soccerdata)
      3. Transfermarkt fallback   — full schedule incl. DFB Pokal (cloud-blocked)

    Set force=true to bypass caches and re-fetch from upstream.
    """
    result = match_data_fetcher.fetch_and_store(season=season, force_refresh=force)

    # Transfermarkt fallback for DFB Pokal and any gaps (best-effort)
    try:
        tm_matches = match_catalogue.fetch_and_store()
        result["transfermarkt_upserted"] = len(tm_matches)
        if "transfermarkt" not in result["sources"]:
            result["sources"].append("transfermarkt")
    except PermissionError as exc:
        result["transfermarkt_note"] = str(exc)
    except Exception as exc:
        result["transfermarkt_note"] = f"skipped: {exc}"

    return result


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
