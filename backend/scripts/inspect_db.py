"""
Human-readable status report for the Bayern analysis database.

Usage:
    python -m backend.scripts.inspect_db
    python -m backend.scripts.inspect_db --match-id 2025-11-01_...
    python -m backend.scripts.inspect_db --events-for 2025-11-01_...
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[3] / ".env")
except ImportError:
    pass

from backend import db


def hr(char: str = "─", width: int = 60) -> None:
    print(char * width)


def fmt_goals(h, a) -> str:
    if h is None:
        return "TBD"
    return f"{h}:{a}"


def section(title: str) -> None:
    print()
    hr()
    print(f"  {title}")
    hr()


def print_overview() -> None:
    matches = db.list_matches()
    if not matches:
        print("\n  No matches in database yet.")
        print("  Run: python -m backend.scripts.run_extraction --match-id all")
        print("  Or:  POST /api/analysis/matches/refresh")
        return

    by_comp: dict[str, list] = {}
    for m in matches:
        by_comp.setdefault(m["competition"], []).append(m)

    section("MATCH CATALOGUE SUMMARY")
    total_analysed = sum(1 for m in matches if m["analysed"])
    print(f"  Total matches: {len(matches)}   Analysed: {total_analysed}/{len(matches)}")

    for comp, ms in sorted(by_comp.items()):
        analysed = sum(1 for m in ms if m["analysed"])
        print(f"\n  {comp} ({len(ms)} matches, {analysed} analysed)")
        for m in ms:
            mark = "✓" if m["analysed"] else "·"
            score = fmt_goals(m["home_goals"], m["away_goals"])
            print(f"    [{mark}] {m['date']}  {m['home_team']} {score} {m['away_team']}")

    section("EVENT STATISTICS")
    try:
        all_off = db.get_all_events(direction="offensive")
        all_def = db.get_all_events(direction="defensive")
        print(f"  Offensive events: {len(all_off)}")
        print(f"  Defensive events: {len(all_def)}")

        if all_off or all_def:
            from collections import Counter
            off_situations = Counter(e["situation"] for e in all_off)
            def_situations = Counter(e["situation"] for e in all_def)

            print("\n  Top offensive situations:")
            for sit, cnt in off_situations.most_common(5):
                print(f"    {cnt:3d}×  {sit}")

            print("\n  Top defensive situations:")
            for sit, cnt in def_situations.most_common(5):
                print(f"    {cnt:3d}×  {sit}")
    except Exception as e:
        print(f"  (Event stats unavailable: {e})")

    section("TEXT SOURCES")
    conn = sqlite3.connect(db.ANALYSIS_DB_PATH)
    rows = conn.execute(
        "SELECT source, COUNT(*) as n FROM text_sources GROUP BY source ORDER BY source"
    ).fetchall()
    conn.close()
    if rows:
        for source, n in rows:
            print(f"  {source:<20} {n} entries")
    else:
        print("  No text sources yet.")


def print_match_detail(match_id: str) -> None:
    m = db.get_match(match_id)
    if not m:
        print(f"Match not found: {match_id}", file=sys.stderr)
        sys.exit(1)

    section(f"MATCH: {m['home_team']} vs {m['away_team']}")
    print(f"  Date:        {m['date']}")
    print(f"  Competition: {m['competition']}")
    print(f"  Result:      {fmt_goals(m['home_goals'], m['away_goals'])}")
    print(f"  Analysed:    {'YES' if m['analysed'] else 'NO'}")

    sources = db.get_text_sources(match_id)
    print(f"\n  Text sources ({len(sources)}):")
    for s in sources:
        chars = len(s["content"]) if s["content"] else 0
        print(f"    {s['source']:<20} {chars:,} chars  (fetched {s['fetched_at'][:19]})")


def print_events(match_id: str) -> None:
    m = db.get_match(match_id)
    if not m:
        print(f"Match not found: {match_id}", file=sys.stderr)
        sys.exit(1)

    events = db.get_match_events(match_id)
    section(f"EVENTS: {m['home_team']} vs {m['away_team']}  ({len(events)} events)")

    for ev in events:
        try:
            players = json.loads(ev["players_involved"] or "[]")
        except Exception:
            players = []
        minute = f"{ev['minute']:3d}'" if ev["minute"] is not None else "  ?'"
        plist = ", ".join(players) if players else "—"
        print(f"\n  {minute}  [{ev['direction'][:3].upper()}]  {ev['type']:<20}  {ev['situation']}")
        print(f"         Players: {plist}")
        if ev["description"]:
            print(f"         \"{ev['description']}\"")
        print(f"         Confidence: {ev['confidence']}")


def main() -> None:
    db.init_analysis_db()

    parser = argparse.ArgumentParser(description="Inspect Bayern analysis database")
    parser.add_argument("--match-id", help="Show detail for a specific match ID")
    parser.add_argument("--events-for", help="Show extracted events for a match ID")
    args = parser.parse_args()

    if args.events_for:
        print_events(args.events_for)
    elif args.match_id:
        print_match_detail(args.match_id)
    else:
        print_overview()

    print()


if __name__ == "__main__":
    main()
