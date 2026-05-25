"""
CLI: run text fetch + LLM extraction for Bayern match(es).

Usage:
    python -m backend.scripts.run_extraction --match-id all
    python -m backend.scripts.run_extraction --match-id 2025-11-02_bayer-leverkusen_fc-bayernmuenchen
    python -m backend.scripts.run_extraction --fetch-only --match-id all
"""
import argparse
import os
import sys
from pathlib import Path

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[3] / ".env")
except ImportError:
    pass

from backend import db
from backend.app.services import text_fetcher, llm_extractor


def process_match(match: dict, fetch: bool, extract: bool) -> None:
    print(f"\n[{match['id']}] {match['date']} — {match['home_team']} vs {match['away_team']}")

    if fetch:
        results = text_fetcher.fetch_all_text(match)
        for src, content in results.items():
            status = f"{len(content)} chars" if content else "not found"
            print(f"  {src}: {status}")

    if extract:
        texts = db.get_text_sources(match["id"])
        if not texts:
            print("  extract: no text sources — skipping")
            return
        events = llm_extractor.extract_match_events(match["id"], texts)
        print(f"  extract: {len(events)} events stored")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bayern match extraction CLI")
    parser.add_argument("--match-id", required=True, help="Match ID or 'all'")
    parser.add_argument("--fetch-only", action="store_true", help="Only fetch text, skip LLM extraction")
    parser.add_argument("--extract-only", action="store_true", help="Only run LLM extraction (text must already exist)")
    parser.add_argument("--reextract", action="store_true", help="Re-extract already-analysed matches")
    args = parser.parse_args()

    db.init_analysis_db()

    do_fetch = not args.extract_only
    do_extract = not args.fetch_only

    if args.match_id == "all":
        matches = db.list_matches()
        if not args.reextract:
            if do_extract and not do_fetch:
                matches = [m for m in matches if not m["analysed"]]
        if not matches:
            print("No matches to process.")
            return
        for match in matches:
            process_match(match, fetch=do_fetch, extract=do_extract)
    else:
        match = db.get_match(args.match_id)
        if not match:
            print(f"Match not found: {args.match_id}", file=sys.stderr)
            sys.exit(1)
        process_match(match, fetch=do_fetch, extract=do_extract)


if __name__ == "__main__":
    main()
