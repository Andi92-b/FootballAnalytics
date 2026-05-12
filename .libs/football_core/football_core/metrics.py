"""
metrics.py — metric formula implementations.

All formulae match metric-definitions.md exactly. Do not deviate.
"""


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
    return _get(stats, "standard.Playing Time_Min", "standard.Min", "standard.Playing_Time_Min", default=1.0) or 1.0


def _per90(value: float, stats: dict) -> float:
    return value / (_minutes(stats) / 90)


def _poss_adj(value: float, stats: dict) -> float:
    team_poss = _get(stats, "standard.team_poss", default=0.5)
    denom = 1.0 - team_poss
    return value / denom if denom > 0 else 0.0


# ── Defence ──────────────────────────────────────────────────────────────────

def front_foot_defending(stats: dict) -> float:
    """(Tkl + Challenges.Att + Fls + Int + Blocks.Pass) / 90 ÷ (1 – team_poss)"""
    tkl = _get(stats, "defense.Tkl", "defense.Tackles_Tkl")
    ch_att = _get(stats, "defense.Challenges_Att", "defense.Challenges.Att")
    fls = _get(stats, "misc.Fls", "misc.Performance_Fls")
    int_ = _get(stats, "defense.Int")
    blk_pass = _get(stats, "defense.Blocks_Pass", "defense.Blocks.Pass")
    raw = _per90(tkl + ch_att + fls + int_ + blk_pass, stats)
    return _poss_adj(raw, stats)


def tackle_success(stats: dict) -> float:
    """Challenges.Tkl% (pre-computed by FBref)"""
    return _get(stats, "defense.Challenges_Tkl%", "defense.Tkl%", "defense.Challenges.Tkl%")


def back_foot_defending(stats: dict) -> float:
    """(Blocks.Sh + Clr) / 90 ÷ (1 – team_poss)"""
    blk_sh = _get(stats, "defense.Blocks_Sh", "defense.Blocks.Sh")
    clr = _get(stats, "defense.Clr")
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
    """(0.8 × xAG + 0.2 × Ast) / 90"""
    xag = _get(stats, "passing.xAG", "standard.xAG")
    ast = _get(stats, "standard.Ast")
    return _per90(0.8 * xag + 0.2 * ast, stats)


def cross_volume(stats: dict) -> float:
    """Crs / (Att3rd_touches / 100)"""
    crs = _get(stats, "passing_types.Crs")
    att3rd = _get(stats, "possession.Touches_Att3rd", "possession.Touches.Att3rd")
    return crs / (att3rd / 100) if att3rd > 0 else 0.0


def dribble_volume(stats: dict) -> float:
    """Dribbles.Att / (Touches / 100)"""
    drb = _get(stats,
               "possession.Dribbles_Att", "possession.Take-Ons_Att",
               "possession.Dribbles.Att")
    touches = _get(stats, "possession.Touches", "possession.Touches_Touches")
    return drb / (touches / 100) if touches > 0 else 0.0


def pass_progression(stats: dict) -> float:
    """Prog / Total.Att"""
    prog = _get(stats, "passing.Prog", "passing.PrgP")
    total = _get(stats, "passing.Total_Att", "passing.Att", "passing.Total.Att")
    return prog / total if total > 0 else 0.0


def carry_progression(stats: dict) -> float:
    """PrgC / Carries"""
    prgc = _get(stats, "possession.PrgC", "possession.Carries_PrgC")
    carries = _get(stats, "possession.Carries", "possession.Carries_Carries")
    return prgc / carries if carries > 0 else 0.0


def progressive_receptions(stats: dict) -> float:
    """PrgR / Rec"""
    prgr = _get(stats, "possession.Receiving_PrgR", "possession.PrgR")
    rec = _get(stats, "possession.Receiving_Rec", "possession.Rec")
    return prgr / rec if rec > 0 else 0.0


# ── Attack ───────────────────────────────────────────────────────────────────

def goal_threat(stats: dict) -> float:
    """(0.7 × npxG + 0.3 × (Gls – PK)) / 90"""
    npxg = _get(stats, "shooting.npxG", "shooting.Expected_npxG")
    gls = _get(stats, "standard.Gls")
    pk = _get(stats, "standard.PK")
    return _per90(0.7 * npxg + 0.3 * (gls - pk), stats)


def shot_frequency(stats: dict) -> float:
    """Sh / (Touches / 100)"""
    sh = _get(stats, "shooting.Sh", "shooting.Standard_Sh")
    touches = _get(stats, "possession.Touches", "possession.Touches_Touches")
    return sh / (touches / 100) if touches > 0 else 0.0


def box_threat(stats: dict) -> float:
    """AttPen_touches / (Mid3rd_touches + Att3rd_touches)"""
    att_pen = _get(stats, "possession.Touches_AttPen", "possession.Touches.AttPen")
    mid3rd = _get(stats, "possession.Touches_Mid3rd", "possession.Touches.Mid3rd")
    att3rd = _get(stats, "possession.Touches_Att3rd", "possession.Touches.Att3rd")
    denom = mid3rd + att3rd
    return att_pen / denom if denom > 0 else 0.0


def shot_quality(stats: dict) -> float:
    """npxG/Sh (pre-computed by FBref)"""
    return _get(stats, "shooting.npxG/Sh", "shooting.Expected_npxG/Sh")


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
