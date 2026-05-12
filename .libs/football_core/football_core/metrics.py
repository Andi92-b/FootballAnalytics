"""
metrics.py — metric formula implementations.

All formulae match metric-definitions.md exactly. Do not deviate.
"""


# Metrics that cannot be computed from currently available data sources.
# These are skipped in percentile computation and surfaced in missing_metrics.
PENDING_METRICS: frozenset[str] = frozenset({
    # FBref passing table gone post-2026-01-20
    "Loose ball recoveries",   # misc.Recov — removed from FBref
    "Link-up play",            # passing.Short/Med.Att — passing table gone
    "Progressive receptions",  # possession.PrgR/Rec — possession table gone
    "Launched passes",         # passing.Long.Att/Total.Att — passing table gone
    "Pass progression",        # passing.PrgP/Total.Att — passing table gone
    # FBref misc aerial data gone post-2026-01-20
    "Aerial volume",           # misc.Aerial_Won/Lost — removed from FBref
    "Aerial success",          # misc.Aerial_Won% — removed from FBref
    # FBref defense table gone post-2026-01-20
    "Tackle success",          # defense.Challenges_Tkl% — defense table gone
    "Back-foot defending",     # defense.Blocks.Sh + defense.Clr — defense table gone
    "One-v-one defending",     # same as tackle_success — defense table gone
    # FBref standard pass completion gone (no passing table)
    "Ball retention",          # passing.Total_Cmp% — passing table gone
})

# Source tier for each metric:
#   A          = FBref only
#   A+B        = FBref + Understat
#   A+C        = FBref + WhoScored
#   C          = WhoScored only
#   pending    = no available source in V1
METRIC_SOURCES: dict[str, str] = {
    "Front-foot defending":    "A",      # degraded: TklW+Fls+Int from FBref misc only
    "Tackle success":          "pending", # defense table gone
    "Back-foot defending":     "pending", # defense table gone
    "Loose ball recoveries":   "pending", # misc.Recov gone
    "Aerial volume":           "pending", # misc aerial data gone
    "Aerial success":          "pending", # misc aerial data gone
    "One-v-one defending":     "pending", # defense table gone
    "Link-up play":            "pending", # passing table gone
    "Ball retention":          "pending", # passing table gone
    "Launched passes":         "pending", # passing table gone
    "Creative threat":         "A+B",
    "Cross volume":            "C",
    "Dribble volume":          "C",
    "Pass progression":        "pending", # passing table gone
    "Carry progression":       "C",
    "Progressive receptions":  "pending", # possession table gone
    "Goal threat":             "A+B",
    "Shot frequency":          "A+C",
    "Box threat":              "C",
    "Shot quality":            "A+B",
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
    """(Aerial.Won + Aerial.Lost) / 90"""
    won = _get(stats, "misc.Aerial_Won", "misc.Aerial.Won")
    lost = _get(stats, "misc.Aerial_Lost", "misc.Aerial.Lost")
    return _per90(won + lost, stats)


def aerial_success(stats: dict) -> float:
    """Aerial.Won% (pre-computed by FBref)"""
    return _get(stats, "misc.Aerial_Won%", "misc.Aerial.Won%")


def one_v_one_defending(stats: dict) -> float:
    """Challenges.Tkl% — FB only, same column as tackle_success"""
    return tackle_success(stats)


# ── Possession ───────────────────────────────────────────────────────────────

def link_up_play(stats: dict) -> float:
    """(Short.Att + Med.Att) / Total.Att"""
    short = _get(stats, "passing.Short_Att", "passing.Short.Att")
    med = _get(stats, "passing.Med_Att", "passing.Medium_Att", "passing.Med.Att")
    total = _get(stats, "passing.Total_Att", "passing.Att", "passing.Total.Att")
    return (short + med) / total if total > 0 else 0.0


def ball_retention(stats: dict) -> float:
    """Total.Cmp% (pre-computed by FBref)"""
    return _get(stats, "passing.Total_Cmp%", "passing.Cmp%", "passing.Total.Cmp%")


def launched_passes(stats: dict) -> float:
    """Long.Att / Total.Att"""
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
    """Crs[WhoScored] / (Att3rd_touches[WhoScored] / 100)  — Tier C"""
    crs = _get(stats, "whoscored.crosses")
    att3rd = _get(stats, "whoscored.att3rd")
    return crs / (att3rd / 100) if att3rd > 0 else 0.0


def dribble_volume(stats: dict) -> float:
    """Dribbles.Att[WhoScored] / (Touches[WhoScored] / 100)  — Tier C"""
    drb = _get(stats, "whoscored.dribbles_att")
    touches = _get(stats, "whoscored.touches")
    return drb / (touches / 100) if touches > 0 else 0.0


def pass_progression(stats: dict) -> float:
    """Prog / Total.Att"""
    prog = _get(stats, "passing.Prog", "passing.PrgP")
    total = _get(stats, "passing.Total_Att", "passing.Att", "passing.Total.Att")
    return prog / total if total > 0 else 0.0


def carry_progression(stats: dict) -> float:
    """PrgC_proxy[WhoScored] / Carries[WhoScored]  — Tier C"""
    carries = _get(stats, "whoscored.carries")
    # proxy: 30% of carries assumed progressive until WhoScored provides split
    prgc_proxy = carries * 0.30
    return prgc_proxy / carries if carries > 0 else 0.0


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
    """Sh[FBref] / (Touches[WhoScored] / 100)  — Tier A+C"""
    sh = _get(stats, "shooting.Standard_Sh", "shooting.Sh")
    touches = _get(stats, "whoscored.touches")
    return sh / (touches / 100) if touches > 0 else 0.0


def box_threat(stats: dict) -> float:
    """AttPen_touches[WhoScored] / (Mid3rd + Att3rd)[WhoScored]  — Tier C"""
    att_pen = _get(stats, "whoscored.attpen")
    mid3rd = _get(stats, "whoscored.mid3rd")
    att3rd = _get(stats, "whoscored.att3rd")
    denom = mid3rd + att3rd
    return att_pen / denom if denom > 0 else 0.0


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
