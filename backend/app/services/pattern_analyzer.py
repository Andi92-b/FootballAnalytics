"""
Aggregates match_events into a PatternReport — frequency tables and supporting quotes
grouped by situation, direction, and competition.
"""
import json
from collections import Counter, defaultdict

from pydantic import BaseModel

from backend import db


class SituationPattern(BaseModel):
    situation: str
    trigger: str | None
    count: int
    quotes: list[str]
    competition_breakdown: dict[str, int]


class PatternReport(BaseModel):
    defensive: list[SituationPattern]
    offensive: list[SituationPattern]
    total_matches_analysed: int
    goals_conceded: int
    goals_scored: int
    competition_summary: dict[str, dict]


def build_report(competition: str | None = None) -> PatternReport:
    """
    Build a PatternReport from all stored match events.

    Optionally filtered to a single competition.
    """
    matches = db.list_matches(competition=competition)
    analysed_ids = {m["id"] for m in matches if m["analysed"]}

    def _aggregate(direction: str) -> list[SituationPattern]:
        events = db.get_all_events(direction=direction, competition=competition)
        # Only include events from analysed matches
        events = [e for e in events if e["match_id"] in analysed_ids]

        # Group by (situation, trigger)
        groups: dict[tuple, list[dict]] = defaultdict(list)
        for ev in events:
            key = (ev.get("situation") or "unknown", ev.get("trigger"))
            groups[key].append(ev)

        patterns: list[SituationPattern] = []
        for (situation, trigger), evs in sorted(groups.items(), key=lambda x: -len(x[1])):
            comp_breakdown: Counter = Counter()
            quotes: list[str] = []
            for ev in evs:
                comp = ev.get("competition", "Unknown")
                comp_breakdown[comp] += 1
                desc = ev.get("description")
                if desc and ev.get("confidence") in ("high", "medium") and len(quotes) < 5:
                    quotes.append(desc)

            patterns.append(
                SituationPattern(
                    situation=situation,
                    trigger=trigger,
                    count=len(evs),
                    quotes=quotes,
                    competition_breakdown=dict(comp_breakdown),
                )
            )

        return patterns

    all_events = db.get_all_events(competition=competition)
    analysed_events = [e for e in all_events if e["match_id"] in analysed_ids]

    goals_scored = sum(
        1 for e in analysed_events
        if e.get("type") == "goal" and e.get("direction") == "offensive"
    )
    goals_conceded = sum(
        1 for e in analysed_events
        if e.get("type") == "goal" and e.get("direction") == "defensive"
    )

    # Per-competition summary: W/D/L, goals for/against
    comp_summary: dict[str, dict] = defaultdict(lambda: {"W": 0, "D": 0, "L": 0, "gf": 0, "ga": 0})
    for m in matches:
        if m["home_goals"] is None:
            continue
        comp = m["competition"]
        is_home = "FC Bayern" in (m["home_team"] or "") or "Bayern München" in (m["home_team"] or "")
        gf = m["home_goals"] if is_home else m["away_goals"]
        ga = m["away_goals"] if is_home else m["home_goals"]
        comp_summary[comp]["gf"] += gf or 0
        comp_summary[comp]["ga"] += ga or 0
        if gf is not None and ga is not None:
            if gf > ga:
                comp_summary[comp]["W"] += 1
            elif gf == ga:
                comp_summary[comp]["D"] += 1
            else:
                comp_summary[comp]["L"] += 1

    return PatternReport(
        defensive=_aggregate("defensive"),
        offensive=_aggregate("offensive"),
        total_matches_analysed=len(analysed_ids),
        goals_conceded=goals_conceded,
        goals_scored=goals_scored,
        competition_summary={k: dict(v) for k, v in comp_summary.items()},
    )
