"""
percentiles.py — position mapping, peer group filtering, percentile computation.
"""

import math

import pandas as pd
from scipy.stats import percentileofscore

from football_core.models import MetricResult, PeerEntry, PositionProfile, SimilarPlayer
from football_core.metrics import compute_metric_values, PENDING_METRICS, METRIC_SOURCES

# ── Position mapping ──────────────────────────────────────────────────────────

POSITION_MAP: dict[str, str] = {
    "CB": "CB",
    "DF": "CB",
    "RB": "FB", "LB": "FB", "RWB": "FB", "LWB": "FB",
    "DM": "DM",
    "CM": "CM", "MF": "CM",
    "AM": "AM",
    "RW": "W", "LW": "W", "LM": "W", "RM": "W",
    "CF": "CF", "FW": "CF", "ST": "CF",
    "GK": "GK",
}

# Multi-part FBref position strings (e.g. "MF,FW", "FW,MF", "DF,MF")
# Resolved in order: first recognised part wins.
POSITION_MAP_MULTI: dict[str, str] = {
    "MF,FW": "W",
    "FW,MF": "W",
    "DF,MF": "DM",
    "MF,DF": "DM",
    "DF,FW": "FB",
    "FW,DF": "FB",
}

# ── Position × metric matrix ──────────────────────────────────────────────────
# ✓ and ~ both map to True (included). – maps to False.

_D = "Defence"
_P = "Possession"
_PR = "Progression"
_A = "Attack"

POSITION_MATRIX: dict[str, list[tuple[str, str]]] = {
    # CB — centre-backs: solid defensive base + distribution style
    "CB": [
        ("Front-foot defending", _D),
        ("Tackle success",       _D),
        ("Back-foot defending",  _D),
        ("Aerial volume",        _D),
        ("Aerial success",       _D),
        ("Ball recovery",        _D),
        ("Ball retention",       _P),
        ("Link-up play",         _P),
        ("Launched passes",      _P),
        ("Pass progression",     _PR),
    ],
    # FB — full-backs: defensive solidity + creative output in wide areas
    "FB": [
        ("Front-foot defending", _D),
        ("Tackle success",       _D),
        ("One-v-one defending",  _D),
        ("Back-foot defending",  _D),
        ("Ball recovery",        _D),
        ("Ball retention",       _P),
        ("Link-up play",         _P),
        ("Creative threat",      _PR),
        ("Cross volume",         _PR),
        ("Cross accuracy",       _PR),
        ("Dribble volume",       _PR),
        ("Dribble success",      _PR),
        ("Foul drawing",         _PR),
        ("Goal threat",          _A),
    ],
    # DM — defensive midfielders: defensive anchor + progressive distribution
    "DM": [
        ("Front-foot defending", _D),
        ("Tackle success",       _D),
        ("One-v-one defending",  _D),
        ("Back-foot defending",  _D),
        ("Aerial success",       _D),
        ("Ball recovery",        _D),
        ("Ball retention",       _P),
        ("Link-up play",         _P),
        ("Launched passes",      _P),
        ("Pass progression",     _PR),
        ("Creative threat",      _PR),
    ],
    # CM — central midfielders: all-round: defend, retain, progress, threaten
    "CM": [
        ("Front-foot defending", _D),
        ("Tackle success",       _D),
        ("Ball recovery",        _D),
        ("Ball retention",       _P),
        ("Link-up play",         _P),
        ("Pass progression",     _PR),
        ("Creative threat",      _PR),
        ("Dribble volume",       _PR),
        ("Dribble success",      _PR),
        ("Foul drawing",         _PR),
        ("Goal threat",          _A),
        ("Shot frequency",       _A),
        ("Shot quality",         _A),
    ],
    # AM — attacking midfielders: progression + creation + finishing
    "AM": [
        ("Ball retention",       _P),
        ("Link-up play",         _P),
        ("Pass progression",     _PR),
        ("Creative threat",      _PR),
        ("Cross volume",         _PR),
        ("Cross accuracy",       _PR),
        ("Dribble volume",       _PR),
        ("Dribble success",      _PR),
        ("Foul drawing",         _PR),
        ("Goal threat",          _A),
        ("Box threat",           _A),
        ("Shot frequency",       _A),
        ("Shot quality",         _A),
    ],
    # W — wingers: drive, create, deliver, and score
    "W": [
        ("Dribble volume",       _PR),
        ("Dribble success",      _PR),
        ("Creative threat",      _PR),
        ("Cross volume",         _PR),
        ("Cross accuracy",       _PR),
        ("Foul drawing",         _PR),
        ("Aerial success",       _D),
        ("Ball retention",       _P),
        ("Goal threat",          _A),
        ("Box threat",           _A),
        ("Shot frequency",       _A),
        ("Shot accuracy",        _A),
        ("Shot quality",         _A),
    ],
    # CF — centre-forwards: aerial, hold-up, movement, and finishing
    "CF": [
        ("Aerial success",       _D),
        ("Foul drawing",         _PR),
        ("Dribble volume",       _PR),
        ("Dribble success",      _PR),
        ("Ball retention",       _P),
        ("Creative threat",      _PR),
        ("Goal threat",          _A),
        ("Box threat",           _A),
        ("Runs in behind",       _A),
        ("Shot frequency",       _A),
        ("Shot accuracy",        _A),
        ("Shot quality",         _A),
    ],
    "GK": [],  # GK profiles not implemented yet
}


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between two metric-value dicts (common keys only)."""
    keys = [k for k in a if k in b]
    if not keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in keys)
    norm_a = math.sqrt(sum(a[k] ** 2 for k in keys))
    norm_b = math.sqrt(sum(b[k] ** 2 for k in keys))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def map_position(fbref_pos_string: str) -> str:
    """Map a raw FBref position string to a position bucket."""
    s = fbref_pos_string.strip()
    # Exact multi-part match first (e.g. "MF,FW")
    if s in POSITION_MAP_MULTI:
        return POSITION_MAP_MULTI[s]
    # Single-part or first-part match
    parts = [p.strip() for p in s.split(",")]
    for part in parts:
        if part in POSITION_MAP:
            return POSITION_MAP[part]
    return "CM"  # safe fallback — skip unknowns rather than raising


def get_position_profile(position_bucket: str, fbref_string: str = "") -> PositionProfile:
    """Return the ordered metric list for a position bucket."""
    metrics = POSITION_MATRIX.get(position_bucket)
    if metrics is None:
        raise ValueError(f"Unknown position bucket: {position_bucket!r}")
    return PositionProfile(
        position_bucket=position_bucket,
        fbref_string=fbref_string,
        metrics=[{"name": name, "category": cat} for name, cat in metrics],
    )


def _get_player_pos_string(player_stats: dict) -> str:
    for key in ("standard.pos", "standard.Pos", "standard.Position"):
        val = player_stats.get(key)
        if val and str(val) not in ("nan", "None", ""):
            return str(val)
    return "CB"


def _get_minutes(player_stats: dict) -> float:
    for key in ("standard.Playing Time_Min", "standard.Min", "standard.Playing_Time_Min"):
        val = player_stats.get(key)
        if val is not None:
            try:
                return float(str(val).replace(",", ""))
            except (ValueError, TypeError):
                pass
    return 0.0


def compute_percentiles(
    player_stats: dict,
    all_player_stats: list[dict],
    position_bucket: str,
    min_minutes: int = 900,
    available_sources: list[str] | None = None,
) -> tuple[list[MetricResult], list[str], list[PeerEntry], list[SimilarPlayer]]:
    """
    Compute percentile ranks for the player within their positional peer group.

    Parameters
    ----------
    player_stats       : flat merged dict for the target player (with injected source namespaces)
    all_player_stats   : list of flat merged dicts for all players in the league
    position_bucket    : e.g. "CB"
    min_minutes        : minimum minutes to qualify as a peer
    available_sources  : list of available source names (e.g. ["fbref", "understat"])

    Returns
    -------
    (list[MetricResult], missing_metrics: list[str], peers: list[PeerEntry], similar: list[SimilarPlayer])
    """
    available_sources = available_sources or ["fbref"]
    profile = get_position_profile(position_bucket)
    all_metric_names = [m["name"] for m in profile.metrics]
    metric_cats = {m["name"]: m["category"] for m in profile.metrics}

    # Split metrics into computable vs missing
    missing_metrics: list[str] = []
    metric_names: list[str] = []
    for name in all_metric_names:
        tier = METRIC_SOURCES.get(name, "A")
        # Explicitly pending (data gone from all sources, or no FBref fallback for peer group)
        if name in PENDING_METRICS:
            missing_metrics.append(name)
            continue
        # Tier A+B: requires Understat
        if "B" in tier and "understat" not in available_sources:
            missing_metrics.append(name)
            continue
        # Pure Tier C or A+C (WhoScored-only, no Sofascore fallback coded)
        if tier in ("C", "A+C") and "whoscored" not in available_sources:
            missing_metrics.append(name)
            continue
        # A+SC metrics use FBref fallbacks for peers — always computable
        metric_names.append(name)

    # Build peer group: same position bucket, min minutes
    peers_raw: list[dict] = []
    for p in all_player_stats:
        try:
            pos_str = _get_player_pos_string(p)
            bucket = map_position(pos_str)
        except ValueError:
            continue
        mins = _get_minutes(p)
        if bucket == position_bucket and mins >= min_minutes:
            peers_raw.append(p)

    if not peers_raw:
        peers_raw = [player_stats]  # fallback — at least the player themselves

    # Compute raw values for all peers
    peer_raw_values: dict[str, list[float]] = {name: [] for name in metric_names}
    for peer in peers_raw:
        vals = compute_metric_values(peer, metric_names)
        for name, val in vals.items():
            peer_raw_values[name].append(val)

    # Compute player raw values
    player_raw = compute_metric_values(player_stats, metric_names)

    results: list[MetricResult] = []
    for name in metric_names:
        raw = player_raw[name]
        peer_vals = peer_raw_values[name]
        pct = percentileofscore(peer_vals, raw, kind="rank")
        pct = max(0, min(99, round(pct)))
        source = METRIC_SOURCES.get(name, "fbref")
        results.append(MetricResult(
            name=name,
            category=metric_cats[name],
            raw=raw,
            percentile=pct,
            source=source,
        ))

    # Build PeerEntry list — compute metric values for each peer and attach identity
    peer_entries: list[PeerEntry] = []
    for peer in peers_raw:
        peer_metrics = compute_metric_values(peer, metric_names)
        peer_entries.append(PeerEntry(
            name=str(peer.get("standard.player", peer.get("player", "Unknown"))),
            team=str(peer.get("standard.team", peer.get("team", ""))),
            position=str(_get_player_pos_string(peer)),
            minutes=int(_get_minutes(peer)),
            metric_values={k: round(v, 4) for k, v in peer_metrics.items()},
        ))
    # Sort by minutes descending so top qualifiers appear first
    peer_entries.sort(key=lambda p: -p.minutes)

    # ── Compute similar players (cross-position, all qualifiers, min 900 min) ──
    player_mv = {k: round(v, 4) for k, v in player_raw.items()}
    player_name_key = str(player_stats.get("standard.player", player_stats.get("player", "")))

    similar_candidates: list[SimilarPlayer] = []
    for p_stats in all_player_stats:
        p_name = str(p_stats.get("standard.player", p_stats.get("player", "Unknown")))
        if p_name == player_name_key:
            continue
        p_mins = _get_minutes(p_stats)
        if p_mins < min_minutes:
            continue
        # Compute metric values using the TARGET player's metric list (same namespace)
        p_mv = compute_metric_values(p_stats, metric_names)
        sim = _cosine_similarity(player_mv, p_mv)
        p_pos_bucket = map_position(_get_player_pos_string(p_stats))
        similar_candidates.append(SimilarPlayer(
            name=p_name,
            team=str(p_stats.get("standard.team", p_stats.get("team", ""))),
            position=p_pos_bucket,
            minutes=int(p_mins),
            similarity=round(sim, 4),
            metric_values={k: round(v, 4) for k, v in p_mv.items()},
        ))

    similar_candidates.sort(key=lambda s: -s.similarity)
    similar_players = similar_candidates[:10]

    return results, missing_metrics, peer_entries, similar_players
