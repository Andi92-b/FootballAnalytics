"""
metrics.py — metric formula implementations.

All formulae match metric-definitions.md exactly. Do not deviate.
"""


# Metrics that cannot be computed from currently available data sources.
# These are skipped in percentile computation and surfaced in missing_metrics.
#
# Peer comparison requires the SAME metric to be computable for all league players.
# Sofascore/OVO data is only available for registry players (not the full league),
# so any metric whose formula ONLY works with Sofascore/OVO keys must stay pending
# until we have league-wide Sofascore data.
#
# Exceptions: cross_volume and shot_frequency use FBref columns as fallback for peers
# (misc.Performance_Crs and shooting.Standard_Sh), so those CAN be percentile-ranked.
PENDING_METRICS: frozenset[str] = frozenset({
    # FBref defense table gone
    "Tackle success",          # defense.Challenges_Tkl% — gone
    "Back-foot defending",     # defense.Blocks.Sh — gone
    "One-v-one defending",     # same column — gone
    # FBref possession table gone
    "Progressive receptions",  # possession.PrgR — gone
    # FBref misc column gone
    "Loose ball recoveries",   # misc.Recov — removed from FBref
    # FBref passing table gone, no FBref fallback for peers
    "Launched passes",         # passing.Long.Att — gone; no Sofascore equivalent
    "Link-up play",            # needs own/opp half split — no FBref fallback for peers
    "Ball retention",          # pass% — no FBref fallback for peers (passing table gone)
    "Pass progression",        # passes to opp box — no FBref fallback for peers
    # FBref misc aerial data gone, no FBref fallback for peers
    "Aerial volume",           # misc.Aerial — gone; Sofascore available for target player only
    "Aerial success",          # misc.Aerial.Won% — gone; Sofascore for target player only
    # FBref has no dribbles or carry data; Sofascore/OVO only for target player
    "Dribble volume",          # no FBref fallback for peers
    "Carry progression",       # no FBref fallback for peers
})

# Source tier for each metric:
#   A          = FBref only
#   A+B        = FBref + Understat
#   A+C        = FBref + WhoScored
#   C          = WhoScored only
#   pending    = no available source in V1
METRIC_SOURCES: dict[str, str] = {
    "Front-foot defending":    "A",        # FBref misc (TklW+Fls+Int) — full peer comparison
    "Tackle success":          "pending",
    "Back-foot defending":     "pending",
    "Loose ball recoveries":   "pending",
    "Aerial volume":           "pending",  # Sofascore target only; no FBref fallback for peers
    "Aerial success":          "pending",  # Sofascore target only; no FBref fallback for peers
    "One-v-one defending":     "pending",
    "Link-up play":            "pending",  # no FBref fallback for peers
    "Ball retention":          "pending",  # no FBref fallback for peers
    "Launched passes":         "pending",
    "Creative threat":         "A+B",      # Understat xA + FBref Ast — full peer comparison
    "Cross volume":            "A+SC",     # per90: sofascore.totalCross OR misc.Crs (peers)
    "Dribble volume":          "pending",  # no FBref fallback for peers
    "Pass progression":        "pending",  # no FBref fallback for peers
    "Carry progression":       "pending",  # no FBref fallback for peers
    "Progressive receptions":  "pending",
    "Goal threat":             "A+B",      # Understat npxG + FBref goals — full peer comparison
    "Shot frequency":          "A+SC",     # per90: sofascore.totalShots OR shooting.Sh (peers)
    "Box threat":              "pending",  # Sofascore target only; no FBref split for peers
    "Shot quality":            "A+B",      # Understat npxG / shots — full peer comparison
}

def _get(stats: dict, *keys: str, default: float = 0.0) -> float:
    """Return the first key found in stats, cast to float. Returns default if missing/NaN."""
    for key in keys:
        val = stats.get(key)
        if val is not None:
            try:
                f = float(val)
                import math
                if math.isnan(f) or math.isinf(f):
                    return default
                return f
            except (ValueError, TypeError):
                pass
    return default


def _minutes(stats: dict) -> float:
    return _get(
        stats,
        "standard.Playing Time_Min", "standard.Min", "standard.Playing_Time_Min",
        "standard.Playing Time_90s",
        default=1.0,
    ) or 1.0


def _90s(stats: dict) -> float:
    """Number of 90-minute periods played (can come from any table's 90s column)."""
    return _get(stats, "standard.Playing Time_90s", "misc.90s", "shooting.90s", default=1.0) or 1.0


def _per90(value: float, stats: dict) -> float:
    return value / (_minutes(stats) / 90)


def _poss_adj(value: float, stats: dict) -> float:
    team_poss = _get(stats, "standard.team_poss", default=0.5)
    denom = 1.0 - team_poss
    return value / denom if denom > 0 else 0.0


# ── Defence ──────────────────────────────────────────────────────────────────

def front_foot_defending(stats: dict) -> float:
    """(TklW + Fls + Int) / 90 ÷ (1 – team_poss)
    Degraded Tier A: uses only FBref misc columns (TklW, Fls, Int).
    Full Tier A+C will add Challenges.Att + Blocks.Pass from WhoScored when available.
    """
    # FBref misc (Tier A) — always available
    tklw = _get(stats, "misc.Performance_TklW", "misc.TklW")
    fls = _get(stats, "misc.Performance_Fls", "misc.Fls")
    int_ = _get(stats, "misc.Performance_Int", "misc.Int")
    # WhoScored (Tier C) — zero when stub active; add when available
    ch_att = _get(stats, "whoscored.challenges_att", default=0.0)
    blk_pass = _get(stats, "whoscored.blocked_passes", default=0.0)
    raw = _per90(tklw + fls + int_ + ch_att + blk_pass, stats)
    return _poss_adj(raw, stats)


def tackle_success(stats: dict) -> float:
    """Challenges.Tkl% (pre-computed by FBref)"""
    return _get(stats, "defense.Challenges_Tkl%", "defense.Tkl%", "defense.Challenges.Tkl%")


def back_foot_defending(stats: dict) -> float:
    """(blocked_shots[WhoScored] + Clr[FBref]) / 90 ÷ (1 – team_poss)
    Tier A+C: WhoScored for blocked shots; FBref misc for clearances.
    """
    blk_sh = _get(stats, "whoscored.blocked_shots")
    clr = _get(stats, "misc.Clr", "misc.Performance_Clr", "defense.Clr")
    raw = _per90(blk_sh + clr, stats)
    return _poss_adj(raw, stats)


def loose_ball_recoveries(stats: dict) -> float:
    """Recov / 90"""
    recov = _get(stats, "misc.Recov", "misc.Performance_Recov")
    return _per90(recov, stats)


def aerial_volume(stats: dict) -> float:
    """(aerialDuelsWon + aerialLost) / 90 — Sofascore (Tier A+SC)"""
    won = _get(stats, "sofascore.aerialDuelsWon", "misc.Aerial_Won", "misc.Aerial.Won")
    lost = _get(stats, "sofascore.aerialLost", "misc.Aerial_Lost", "misc.Aerial.Lost")
    return _per90(won + lost, stats)


def aerial_success(stats: dict) -> float:
    """aerialDuelsWonPercentage — Sofascore (Tier A+SC)"""
    return _get(
        stats,
        "sofascore.aerialDuelsWonPercentage",
        "misc.Aerial_Won%", "misc.Aerial.Won%",
    )


def one_v_one_defending(stats: dict) -> float:
    """Challenges.Tkl% — FB only, same column as tackle_success"""
    return tackle_success(stats)


# ── Possession ───────────────────────────────────────────────────────────────

def link_up_play(stats: dict) -> float:
    """(ownHalfPasses + oppHalfPasses) / totalPasses — Sofascore (Tier A+SC)"""
    own = _get(stats, "sofascore.accurateOwnHalfPasses", "passing.Short_Att", "passing.Short.Att")
    opp = _get(stats, "sofascore.accurateOppositionHalfPasses", "passing.Med_Att", "passing.Med.Att")
    total = _get(stats, "sofascore.totalPasses", "passing.Total_Att", "passing.Att", "passing.Total.Att")
    return (own + opp) / total if total > 0 else 0.0


def ball_retention(stats: dict) -> float:
    """accuratePassesPercentage / 100 — Sofascore (Tier A+SC)"""
    sc_pct = _get(stats, "sofascore.accuratePassesPercentage")
    if sc_pct > 0:
        return sc_pct / 100.0
    return _get(stats, "passing.Total_Cmp%", "passing.Cmp%", "passing.Total.Cmp%") / 100.0


def launched_passes(stats: dict) -> float:
    """Long.Att / Total.Att — passing table gone, no Sofascore equivalent"""
    long_ = _get(stats, "passing.Long_Att", "passing.Long.Att")
    total = _get(stats, "passing.Total_Att", "passing.Att", "passing.Total.Att")
    return long_ / total if total > 0 else 0.0


# ── Progression ──────────────────────────────────────────────────────────────

def creative_threat(stats: dict) -> float:
    """(0.8 × xA[Understat] + 0.2 × Ast[FBref]) / 90  — Tier A+B"""
    xa = _get(stats, "understat.xA")
    ast = _get(stats, "standard.Performance_Ast", "standard.Ast")
    return _per90(0.8 * xa + 0.2 * ast, stats)


def cross_volume(stats: dict) -> float:
    """Crosses / 90  — Tier A+SC.

    Uses sofascore.totalCross for registry players (more complete),
    falls back to misc.Performance_Crs for all FBref-only peers.
    Both are the full-season total, divided by 90s to normalise.
    """
    crs = _get(stats, "sofascore.totalCross", "misc.Performance_Crs", "whoscored.crosses")
    return _per90(crs, stats)


def dribble_volume(stats: dict) -> float:
    """successfulDribbles / 90 — pending: no FBref fallback for peer group."""
    drb = _get(stats, "sofascore.successfulDribbles", "whoscored.dribbles_att")
    return _per90(drb, stats)


def pass_progression(stats: dict) -> float:
    """Prog passes to opp box / 90 — pending: no FBref fallback for peer group."""
    to_box = _get(stats, "ovo.passes_to_opp_box")
    total = _get(stats, "sofascore.totalPasses", "passing.Total_Att", "passing.Att")
    if to_box > 0 and total > 0:
        return to_box / total
    prog = _get(stats, "passing.Prog", "passing.PrgP")
    total_fb = _get(stats, "passing.Total_Att", "passing.Att", "passing.Total.Att")
    return prog / total_fb if total_fb > 0 else 0.0


def carry_progression(stats: dict) -> float:
    """Progressive carries / 90 — pending: no FBref fallback for peer group."""
    prgc = _get(stats, "ovo.progressive_carries", "whoscored.carries")
    return _per90(prgc, stats)


def progressive_receptions(stats: dict) -> float:
    """PrgR / Rec"""
    prgr = _get(stats, "possession.Receiving_PrgR", "possession.PrgR")
    rec = _get(stats, "possession.Receiving_Rec", "possession.Rec")
    return prgr / rec if rec > 0 else 0.0


# ── Attack ───────────────────────────────────────────────────────────────────

def goal_threat(stats: dict) -> float:
    """(0.7 × npxG[Understat] + 0.3 × (Gls – PK)[FBref]) / 90  — Tier A+B"""
    npxg = _get(stats, "understat.npxG")
    gls = _get(stats, "standard.Performance_Gls", "standard.Gls")
    pk = _get(stats, "standard.Performance_PK", "standard.PK")
    return _per90(0.7 * npxg + 0.3 * (gls - pk), stats)


def shot_frequency(stats: dict) -> float:
    """Total shots / 90  — Tier A+SC.

    Uses sofascore.totalShots for registry players,
    falls back to shooting.Standard_Sh for all FBref-only peers.
    Both are full-season totals, divided by 90s for normalisation.
    """
    sh = _get(stats, "sofascore.totalShots", "shooting.Standard_Sh", "shooting.Sh")
    return _per90(sh, stats)


def box_threat(stats: dict) -> float:
    """shotsFromInsideBox / totalShots — pending: no FBref shot-zone split for peers."""
    inside = _get(stats, "sofascore.shotsFromInsideTheBox", "whoscored.attpen")
    total_sh = _get(stats, "sofascore.totalShots", default=1.0) or 1.0
    return inside / total_sh


def shot_quality(stats: dict) -> float:
    """npxG[Understat] / Sh[FBref]  — Tier A+B"""
    npxg = _get(stats, "understat.npxG")
    sh = _get(stats, "shooting.Standard_Sh", "shooting.Sh", default=1.0) or 1.0
    return npxg / sh


# ── Dispatch table ────────────────────────────────────────────────────────────

METRIC_FUNCTIONS: dict[str, callable] = {
    "Front-foot defending": front_foot_defending,
    "Tackle success": tackle_success,
    "Back-foot defending": back_foot_defending,
    "Loose ball recoveries": loose_ball_recoveries,
    "Aerial volume": aerial_volume,
    "Aerial success": aerial_success,
    "One-v-one defending": one_v_one_defending,
    "Link-up play": link_up_play,
    "Ball retention": ball_retention,
    "Launched passes": launched_passes,
    "Creative threat": creative_threat,
    "Cross volume": cross_volume,
    "Dribble volume": dribble_volume,
    "Pass progression": pass_progression,
    "Carry progression": carry_progression,
    "Progressive receptions": progressive_receptions,
    "Goal threat": goal_threat,
    "Shot frequency": shot_frequency,
    "Box threat": box_threat,
    "Shot quality": shot_quality,
}


def compute_metric_values(stats: dict, metric_names: list[str]) -> dict[str, float]:
    """Compute raw values for the requested metrics. Returns {metric_name: float}."""
    result = {}
    for name in metric_names:
        fn = METRIC_FUNCTIONS.get(name)
        if fn is None:
            raise ValueError(f"Unknown metric: {name!r}")
        try:
            result[name] = fn(stats)
        except Exception:
            result[name] = 0.0
    return result
