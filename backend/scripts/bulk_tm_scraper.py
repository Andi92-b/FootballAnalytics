#!/usr/bin/env python3
"""
bulk_tm_scraper.py — Bulk-fetch Transfermarkt positions for all players in the DB.

For each player that doesn't already have a TM cache file:
  1. Search TM by name → resolve player ID
  2. Scrape their profile page → extract main + other positions
  3. Write to .cache/transfermarkt/{name}.json
  4. Upsert into the player_positions table immediately

Skips players that already have a TM cache file (safe to re-run / resume).
Players that TM couldn't resolve are logged to .cache/transfermarkt/_not_found.txt
so they are skipped on subsequent runs.

Usage:
    .venv/bin/python -m backend.scripts.bulk_tm_scraper
    .venv/bin/python -m backend.scripts.bulk_tm_scraper --league "ENG-Premier League"
    .venv/bin/python -m backend.scripts.bulk_tm_scraper --limit 50 --delay 2.0 3.5
    .venv/bin/python -m backend.scripts.bulk_tm_scraper --dry-run

Rate limiting: random delay between requests (default 2–4 s).
With ~1 000 players at 3 s avg ≈ 50 minutes total.
"""
from __future__ import annotations

import argparse
import logging
import random
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_ROOT))

from backend.db import init_db, upsert_player_positions, _conn
from football_core.sources.transfermarkt import fetch_transfermarkt, _TM_POSITION_TO_BUCKET  # type: ignore[attr-defined]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

_CACHE_DIR = _ROOT / ".cache"
_NOT_FOUND_FILE = _CACHE_DIR / "transfermarkt" / "_not_found.txt"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower().strip()


def _safe_filename(s: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", _norm(s))


def _tm_cache_exists(name: str) -> bool:
    path = _CACHE_DIR / "transfermarkt" / f"{_safe_filename(name)}.json"
    return path.exists()


def _load_not_found() -> set[str]:
    if _NOT_FOUND_FILE.exists():
        return {line.strip() for line in _NOT_FOUND_FILE.read_text().splitlines() if line.strip()}
    return set()


def _append_not_found(name: str) -> None:
    _NOT_FOUND_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _NOT_FOUND_FILE.open("a") as f:
        f.write(name + "\n")


def _upsert_tm_result(name: str, tm: dict) -> None:
    """Write a fresh TM result into the player_positions table."""
    upsert_player_positions([{
        "name": name,
        "main_position": tm["main_position"],
        "other_positions": tm.get("other_positions") or [],
        "source": "transfermarkt",
    }])


def _eta_str(done: int, total: int, elapsed: float) -> str:
    if done == 0:
        return "?"
    rate = done / elapsed  # players per second
    remaining = (total - done) / rate
    return str(timedelta(seconds=int(remaining)))


# ── Main ──────────────────────────────────────────────────────────────────────

def run(
    league: str | None,
    limit: int | None,
    delay_range: tuple[float, float],
    dry_run: bool,
) -> None:
    init_db()

    # Load all players from DB (distinct names, highest-minutes row for position)
    with _conn() as c:
        if league:
            rows = c.execute(
                """
                SELECT name FROM players
                WHERE league = ?
                  AND (name, minutes) IN (SELECT name, MAX(minutes) FROM players GROUP BY name)
                ORDER BY name
                """,
                (league,),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT name FROM players
                WHERE (name, minutes) IN (SELECT name, MAX(minutes) FROM players GROUP BY name)
                ORDER BY name
                """
            ).fetchall()

    all_names = [r["name"] for r in rows]

    not_found = _load_not_found()
    log.info("DB players: %d  |  previous not-found: %d", len(all_names), len(not_found))

    # Filter: skip already-cached and previously not-found
    to_scrape = [
        n for n in all_names
        if not _tm_cache_exists(n) and n not in not_found
    ]

    already_cached = len(all_names) - len(to_scrape) - sum(1 for n in all_names if n in not_found)
    log.info(
        "Already cached: %d  |  previously not-found: %d  |  to scrape: %d",
        already_cached,
        sum(1 for n in all_names if n in not_found),
        len(to_scrape),
    )

    if limit:
        to_scrape = to_scrape[:limit]
        log.info("Limiting to first %d players", limit)

    if dry_run:
        log.info("DRY RUN — first 20 players that would be scraped:")
        for n in to_scrape[:20]:
            print(f"  {n}")
        return

    if not to_scrape:
        log.info("Nothing to scrape — all players are already cached.")
        return

    total = len(to_scrape)
    success = 0
    not_found_count = 0
    start_time = time.monotonic()

    log.info("Starting bulk scrape of %d players (delay %.1f–%.1f s)", total, *delay_range)
    print()

    for i, name in enumerate(to_scrape, 1):
        elapsed = time.monotonic() - start_time
        eta = _eta_str(i - 1, total, elapsed) if i > 1 else "?"

        print(
            f"[{i:>4}/{total}]  {name:<35s}  "
            f"elapsed={timedelta(seconds=int(elapsed))}  ETA={eta}",
            end="  ",
            flush=True,
        )

        try:
            tm = fetch_transfermarkt(name, _CACHE_DIR)
        except KeyboardInterrupt:
            print()
            log.info("Interrupted by user after %d/%d players (%d success, %d not found)",
                     i - 1, total, success, not_found_count)
            break
        except Exception as exc:
            print(f"ERROR: {exc}")
            log.warning("Unexpected error for %s: %s", name, exc)
            # Don't mark as not-found for unexpected errors — might be transient
            time.sleep(delay_range[1])  # longer pause on error
            continue

        if tm and tm.get("main_position"):
            _upsert_tm_result(name, tm)
            success += 1
            print(f"✓  {tm['main_position']}")
        else:
            _append_not_found(name)
            not_found_count += 1
            print("— not found on TM")

        # Rate limiting — random delay to avoid detection
        if i < total:
            delay = random.uniform(*delay_range)
            time.sleep(delay)

    elapsed = time.monotonic() - start_time
    print()
    log.info(
        "Done. %d scraped, %d success (%.0f%%), %d not found on TM — total time %s",
        min(i, total),
        success,
        100 * success / max(i, 1),
        not_found_count,
        timedelta(seconds=int(elapsed)),
    )
    log.info("Run 'python -m backend.scripts.enrich_positions' to re-sync the DB from all cache files.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-fetch Transfermarkt positions for all players in the DB."
    )
    parser.add_argument(
        "--league",
        default=None,
        help="Restrict to one league, e.g. 'ENG-Premier League'",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only scrape the first N players (useful for testing)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        nargs=2,
        metavar=("MIN", "MAX"),
        default=[2.0, 4.0],
        help="Random delay range in seconds between requests (default: 2.0 4.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the players that would be scraped without making any requests",
    )
    args = parser.parse_args()

    run(
        league=args.league,
        limit=args.limit,
        delay_range=(args.delay[0], args.delay[1]),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
