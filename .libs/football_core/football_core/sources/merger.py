"""
sources/merger.py — Merge all three source tiers into a single flat stats dict.

Adds namespaced keys to the existing FBref flat dict:
  understat.npxG, understat.xA, understat.xG, understat.shots
  whoscored.touches, whoscored.att3rd, whoscored.attpen, whoscored.mid3rd,
  whoscored.dribbles_att, whoscored.crosses, whoscored.carries,
  whoscored.tackle_success_pct, whoscored.blocked_shots

The merger also records which sources actually contributed data.
"""

from __future__ import annotations

import unicodedata


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower().strip()


def merge_sources(
    player_stats: dict,
    player_name: str,
    understat_data: dict[str, dict] | None,
    whoscored_data: dict[str, dict] | None,
) -> dict:
    """
    Inject Understat and WhoScored data into a player's flat FBref stats dict.

    Parameters
    ----------
    player_stats    : flat FBref merged dict for the player (mutated in-place copy)
    player_name     : display name used for lookup in understat/whoscored dicts
    understat_data  : league-wide Understat dict keyed by normalised name, or None
    whoscored_data  : league-wide WhoScored dict keyed by normalised name, or None

    Returns
    -------
    merged dict with additional namespaced keys injected
    """
    result = dict(player_stats)
    key = _normalize(player_name)

    # ── Tier B: Understat ─────────────────────────────────────────────────────
    if understat_data is not None:
        ud = understat_data.get(key) or {}
        result["understat.npxG"] = float(ud.get("npxG", 0))
        result["understat.xA"] = float(ud.get("xA", 0))
        result["understat.xG"] = float(ud.get("xG", 0))
        result["understat.shots"] = float(ud.get("shots", 0))
    else:
        result["understat.npxG"] = 0.0
        result["understat.xA"] = 0.0
        result["understat.xG"] = 0.0
        result["understat.shots"] = 0.0

    # ── Tier C: WhoScored ─────────────────────────────────────────────────────
    if whoscored_data is not None:
        wd = whoscored_data.get(key) or {}
        result["whoscored.touches"] = float(wd.get("touches", 0))
        result["whoscored.att3rd"] = float(wd.get("att_third_touches", 0))
        result["whoscored.attpen"] = float(wd.get("att_pen_touches", 0))
        result["whoscored.mid3rd"] = float(wd.get("mid_third_touches", 0))
        result["whoscored.dribbles_att"] = float(wd.get("dribbles_att", 0))
        result["whoscored.crosses"] = float(wd.get("crosses", 0))
        result["whoscored.carries"] = float(wd.get("carries", 0))
        result["whoscored.tackle_success_pct"] = float(wd.get("tackle_success_pct", 0))
        result["whoscored.blocked_shots"] = float(wd.get("blocked_shots", 0))
    else:
        for k in (
            "touches", "att3rd", "attpen", "mid3rd",
            "dribbles_att", "crosses", "carries",
            "tackle_success_pct", "blocked_shots",
        ):
            result[f"whoscored.{k}"] = 0.0

    return result
