"""
metrics.py — metric formula implementations.

All formulae match metric-definitions.md exactly. Do not deviate.
"""


# Metrics that cannot be computed from currently available data sources.
# These are skipped in percentile computation and surfaced in missing_metrics.
PENDING_METRICS: frozenset[str] = frozenset({
    # FBref tables removed in Jan 2026; no Sofascore equivalent exists:
    "Carry progression",       # progressive carries — no SC field
    "Progressive receptions",  # progressive passes received — no SC field
    "Loose ball recoveries",   # legacy name; replaced by Ball recovery
})

# Source tier for each metric:
#   A          = FBref only
#   A+B        = FBref + Understat
#   A+C        = FBref + WhoScored
#   C          = WhoScored only
#   pending    = no available source in V1
METRIC_SOURCES: dict[str, str] = {
    "Front-foot defending":    "A",     # FBref misc TklW+Fls+Int
    "Creative threat":         "A+B",   # Understat xA + FBref Ast
    "Cross volume":            "A+SC",  # sofascore.totalCross OR misc.Crs for peers
    "Goal threat":             "A+B",   # Understat npxG + FBref goals
    "Shot frequency":          "SC",    # sofascore.totalShots / touches per 100
    "Shot quality":            "A+B",   # Understat npxG / shots
    "Shot accuracy":           "A",     # FBref shooting.SoT%
    "Foul drawing":            "A",     # FBref misc.Fld
    "Runs in behind":          "A",     # FBref misc.Off/90
    "Tackle success":          "SC",    # sofascore.tacklesWonPercentage
    "Aerial volume":           "SC",    # sofascore.(aerialDuelsWon+aerialLost)/90
    "Aerial success":          "SC",    # sofascore.aerialDuelsWonPercentage
    "Dribble volume":          "SC",    # sofascore.successfulDribbles / touches per 100
    "Ball recovery":           "SC",    # sofascore.ballRecovery/90
    "Back-foot defending":     "SC",    # sofascore.(clearances+blockedShots)/90
    "One-v-one defending":     "SC",    # sofascore.(totalContest-dribbledPast)/totalContest
    "Ball retention":          "SC",    # sofascore.accuratePassesPercentage
    "Launched passes":         "SC",    # sofascore.totalLongBalls/totalPasses
    "Link-up play":            "SC",    # sofascore.(totalPasses-totalLongBalls)/totalPasses
    "Pass progression":        "SC",    # sofascore.accurateFinalThirdPasses/totalPasses
    "Box threat":              "SC",    # sofascore.shotsFromInsideTheBox/totalShots
    "Cross accuracy":          "SC",    # sofascore.accurateCrossesPercentage
    "Dribble success":         "SC",    # sofascore.successfulDribblesPercentage
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
    """tacklesWonPercentage — Sofascore league stats (Tier SC).
    Falls back to FBref defense table (removed Jan 2026, so usually 0 for peer group).
    """
    return _get(stats, "sofascore.tacklesWonPercentage",
                "defense.Challenges_Tkl%", "defense.Tkl%", "defense.Challenges.Tkl%")


def back_foot_defending(stats: dict) -> float:
    """(clearances + blockedShots) / 90 — Sofascore league stats (Tier SC).
    Reactive defensive actions: cleared balls and blocked shots.
    Falls back to FBref misc clearances if SC unavailable.
    """
    clr = _get(stats, "sofascore.clearances", "misc.Clr", "misc.Performance_Clr")
    blk = _get(stats, "sofascore.blockedShots", "whoscored.blocked_shots")
    return _per90(clr + blk, stats)


def loose_ball_recoveries(stats: dict) -> float:
    """Recov / 90"""
    recov = _get(stats, "misc.Recov", "misc.Performance_Recov")
    return _per90(recov, stats)


def ball_recovery(stats: dict) -> float:
    """ballRecovery / 90 — Sofascore league stats (Tier SC).
    Counts pressing actions that won the ball back.
    """
    return _per90(_get(stats, "sofascore.ballRecovery"), stats)


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
    """% of dribble challenges won — Sofascore league stats (Tier SC).
    (totalContest - dribbledPast) / totalContest
    Measures how often a player stops a dribbler in a direct challenge.
    """
    total = _get(stats, "sofascore.totalContest")
    past = _get(stats, "sofascore.dribbledPast")
    if total > 0:
        return max(0.0, (total - past) / total) * 100
    # Fallback: tackle success as a rough proxy
    return tackle_success(stats)


# ── Possession ───────────────────────────────────────────────────────────────

def link_up_play(stats: dict) -> float:
    """% of passes that are NOT long balls — Sofascore league stats (Tier SC).
    Proxy for The Athletic's (short+medium) / total passes.
    High = metronomic passer who keeps play ticking; Low = direct.
    """
    total = _get(stats, "sofascore.totalPasses")
    long_ = _get(stats, "sofascore.totalLongBalls")
    if total > 0:
        return max(0.0, (total - long_) / total) * 100
    # FBref passing table fallback (usually gone)
    own = _get(stats, "passing.Short_Att", "passing.Short.Att")
    opp = _get(stats, "passing.Med_Att", "passing.Med.Att")
    total_fb = _get(stats, "passing.Total_Att", "passing.Att", "passing.Total.Att")
    return (own + opp) / total_fb * 100 if total_fb > 0 else 0.0


def ball_retention(stats: dict) -> float:
    """Pass completion % — Sofascore league stats (Tier SC).
    High = careful, possession-minded player.
    """
    sc_pct = _get(stats, "sofascore.accuratePassesPercentage")
    if sc_pct > 0:
        return sc_pct
    # FBref passing table fallback (usually gone post Jan 2026)
    return _get(stats, "passing.Total_Cmp%", "passing.Cmp%", "passing.Total.Cmp%")


def launched_passes(stats: dict) -> float:
    """totalLongBalls / totalPasses × 100 — Sofascore league stats (Tier SC).
    High = direct/vertical style; Low = short-passing build-up.
    """
    long_ = _get(stats, "sofascore.totalLongBalls")
    total = _get(stats, "sofascore.totalPasses")
    if total > 0:
        return long_ / total * 100
    # FBref fallback (passing table usually gone)
    long_fb = _get(stats, "passing.Long_Att", "passing.Long.Att")
    total_fb = _get(stats, "passing.Total_Att", "passing.Att", "passing.Total.Att")
    return long_fb / total_fb * 100 if total_fb > 0 else 0.0


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


def cross_accuracy(stats: dict) -> float:
    """accurateCrossesPercentage — Sofascore league stats (Tier SC).
    % of crosses that reach a teammate. Separates precision deliverers from
    those who spray crosses in hope. Complements Cross volume.
    """
    pct = _get(stats, "sofascore.accurateCrossesPercentage")
    if pct > 0:
        return pct
    # Fallback: compute from raw counts if percentage isn't available
    accurate = _get(stats, "sofascore.accurateCrosses")
    total = _get(stats, "sofascore.totalCross")
    return accurate / total * 100 if total > 0 else 0.0


def dribble_volume(stats: dict) -> float:
    """successfulDribbles / (touches / 100) — Sofascore league stats (Tier SC).
    Dribbles per 100 touches: accounts for involvement rather than raw volume.
    """
    drb = _get(stats, "sofascore.successfulDribbles", "whoscored.dribbles_att")
    touches = _get(stats, "sofascore.touches")
    if touches > 0:
        return drb / (touches / 100)
    return _per90(drb, stats)


def dribble_success(stats: dict) -> float:
    """successfulDribblesPercentage — Sofascore league stats (Tier SC).
    % of dribble attempts that are completed. Complements Dribble volume:
    volume shows how often a player tries; success shows how good they are at it.
    """
    return _get(stats, "sofascore.successfulDribblesPercentage")


def pass_progression(stats: dict) -> float:
    """accurateFinalThirdPasses / totalPasses × 100 — Sofascore league stats (Tier SC).
    Approximates progressive passing: what share of passes reach the final third.
    High = forward-thinking distributor.
    """
    f3 = _get(stats, "sofascore.accurateFinalThirdPasses")
    total = _get(stats, "sofascore.totalPasses")
    if total > 0:
        return f3 / total * 100
    # OVO / FBref fallbacks (usually unavailable for full peer group)
    to_box = _get(stats, "ovo.passes_to_opp_box")
    prog = _get(stats, "passing.Prog", "passing.PrgP")
    total_fb = _get(stats, "passing.Total_Att", "passing.Att", "passing.Total.Att")
    if to_box > 0 and total_fb > 0:
        return to_box / total_fb * 100
    return prog / total_fb * 100 if total_fb > 0 else 0.0


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
    """totalShots / (touches / 100) — Sofascore league stats (Tier SC).
    Shots per 100 touches: isolates those with eyes for goal from wider contributors.
    Falls back to FBref per-90 when touches unavailable.
    """
    sh = _get(stats, "sofascore.totalShots", "shooting.Standard_Sh", "shooting.Sh")
    touches = _get(stats, "sofascore.touches")
    if touches > 0:
        return sh / (touches / 100)
    return _per90(sh, stats)


def box_threat(stats: dict) -> float:
    """shotsFromInsideTheBox / totalShots × 100 — Sofascore league stats (Tier SC).
    % of shots taken inside the box: separates penalty-box strikers from wide finishers.
    """
    inside = _get(stats, "sofascore.shotsFromInsideTheBox")
    total_sh = _get(stats, "sofascore.totalShots")
    if total_sh > 0:
        return inside / total_sh * 100
    return 0.0


def shot_quality(stats: dict) -> float:
    """npxG[Understat] / Sh[FBref]  — Tier A+B"""
    npxg = _get(stats, "understat.npxG")
    sh = _get(stats, "shooting.Standard_Sh", "shooting.Sh", default=1.0) or 1.0
    return npxg / sh


def shot_accuracy(stats: dict) -> float:
    """Shots on target % — Tier A (FBref shooting.Standard_SoT%).
    Measures technical shooting execution: how often shots are placed on target.
    Complements shot_quality (chance quality) — this is about delivery, not position.
    Derived from The Athletic's player pizza charts methodology.
    """
    return _get(stats, "shooting.Standard_SoT%", "shooting.SoT%") / 100.0


def runs_in_behind(stats: dict) -> float:
    """Offsides caught / 90 — Tier A (FBref misc.Performance_Off).
    Proxy for penetrating forward runs beyond the defensive line.
    Players with high values are consistently making runs in behind.
    Inspired by The Athletic's playstyle wheels 'high line' methodology,
    adapted to player level.
    """
    return _per90(_get(stats, "misc.Performance_Off", "misc.Off"), stats)


def foul_drawing(stats: dict) -> float:
    """Times fouled / 90 — Tier A (FBref misc.Fld).
    For attackers: a proxy for ball-carrying and direct duels won.
    Higher = more involved in direct 1v1 situations that draw fouls.
    """
    fld = _get(stats, "misc.Performance_Fld", "misc.Fld")
    return _per90(fld, stats)


# ── Dispatch table ────────────────────────────────────────────────────────────

METRIC_FUNCTIONS: dict[str, callable] = {
    "Front-foot defending": front_foot_defending,
    "Tackle success": tackle_success,
    "Back-foot defending": back_foot_defending,
    "Loose ball recoveries": loose_ball_recoveries,
    "Aerial volume": aerial_volume,
    "Aerial success": aerial_success,
    "Ball recovery": ball_recovery,
    "One-v-one defending": one_v_one_defending,
    "Link-up play": link_up_play,
    "Ball retention": ball_retention,
    "Launched passes": launched_passes,
    "Creative threat": creative_threat,
    "Cross volume": cross_volume,
    "Cross accuracy": cross_accuracy,
    "Dribble volume": dribble_volume,
    "Dribble success": dribble_success,
    "Pass progression": pass_progression,
    "Carry progression": carry_progression,
    "Progressive receptions": progressive_receptions,
    "Goal threat": goal_threat,
    "Shot frequency": shot_frequency,
    "Box threat": box_threat,
    "Shot quality": shot_quality,
    "Shot accuracy": shot_accuracy,
    "Runs in behind": runs_in_behind,
    "Foul drawing": foul_drawing,
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
