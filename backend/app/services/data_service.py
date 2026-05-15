"""data_service — orchestrates three-tier fetch + percentile computation, with SQLite cache."""
from pathlib import Path
import json
import logging
import unicodedata

from football_core.pipeline import fetch_all
from football_core.fetcher import merge_player_stats, add_team_poss
from football_core.sources.merger import merge_sources
from football_core.percentiles import map_position, compute_percentiles
from football_core.models import PizzaData, MetricResult, PeerEntry, SimilarPlayer, PlayingTimeStats
from football_core.sources.transfermarkt import _TM_POSITION_TO_BUCKET  # type: ignore[attr-defined]
import backend.db as player_db

_CACHE_DIR = Path(__file__).parents[3] / ".cache"
_REGISTRY_PATH = Path(__file__).parents[3] / "player_registry.json"
_FBREF_CACHE_DIR = _CACHE_DIR / "fbref"

log = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Lowercase + strip accents for fuzzy name matching between FBref and Sofascore."""
    return unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode().lower()


def _inject_sc_league_stats(stats: dict, name: str, sc_lookup: dict, sc_lookup_norm: dict) -> dict:
    """Inject Sofascore league stats for one player (peer or target) into their stats dict."""
    sc = sc_lookup.get(name) or sc_lookup_norm.get(_normalize_name(name))
    if sc:
        for k, v in sc.items():
            if k != "_sofascore_id" and v is not None:
                stats.setdefault(f"sofascore.{k}", v)  # don't overwrite richer profile data
    return stats


def _inject_profile_sources(stats: dict, player_name: str, league: str = "", season: int = 0) -> dict:
    """Inject Sofascore and OVO data into the FBref stats dict for the target player."""
    from football_core.pipeline_profile import fetch_profile
    try:
        registry = json.loads(_REGISTRY_PATH.read_text())
    except Exception:
        return stats

    # Build a minimal fallback entry so non-registry players also get
    # Sofascore (auto-resolved from league cache) and OVO (derived from name).
    fallback = {
        "display_name": player_name,
        "name": player_name,
        "fbref_league": league,
        "fbref_season": season,
        "understat_league": league,
        "understat_season": season,
        "understat_name": player_name,
    } if league and season else None

    try:
        result = fetch_profile(player_name, registry, _CACHE_DIR, fallback_entry=fallback)
    except (KeyError, Exception):
        return stats

    ss = result.sources.get("sofascore") or {}
    for k, v in ss.items():
        if v is not None:
            stats[f"sofascore.{k}"] = v

    ovo = result.sources.get("ovo") or {}
    for k, v in (ovo.get("stats") or {}).items():
        if v is not None:
            stats[f"ovo.{k}"] = v

    tm = result.sources.get("transfermarkt") or {}
    for k, v in tm.items():
        if v is not None:
            stats[f"transfermarkt.{k}"] = v

    return stats


def _read_mp_from_cache(player_name: str, league: str, season: int) -> int:
    """
    Fast read of matches played (MP) from the already-cached FBref standard.json.
    Returns 0 if the file doesn't exist or the player isn't found.
    No pandas, no network — pure JSON file read (~1 ms).
    """
    league_slug = league.replace(" ", "_").replace("-", "_")
    path = _FBREF_CACHE_DIR / league_slug / str(season) / "standard.json"
    if not path.exists():
        return 0
    try:
        rows: list[dict] = json.loads(path.read_text())
        norm_target = _normalize_name(player_name)
        for row in rows:
            if _normalize_name(str(row.get("player", ""))) == norm_target:
                return int(row.get("Playing Time_MP") or 0)
    except Exception as exc:
        log.warning("_read_mp_from_cache failed: %s", exc)
    return 0


def _pizza_data_from_dict(d: dict) -> PizzaData:
    """Reconstruct a PizzaData from its model_dump() output stored in SQLite."""
    pt = d.get("playing_time")
    return PizzaData(
        player=d["player"],
        position=d["position"],
        season=d["season"],
        league=d["league"],
        metrics=[MetricResult(**m) for m in d.get("metrics", [])],
        missing_metrics=d.get("missing_metrics", []),
        data_sources=d.get("data_sources", []),
        data_freshness=d.get("data_freshness", {}),
        svg=d.get("svg"),
        peers=[PeerEntry(**p) for p in d.get("peers", [])],
        similar_players=[SimilarPlayer(**s) for s in d.get("similar_players", [])],
        playing_time=PlayingTimeStats(**pt) if pt else None,
        raw_stats=d.get("raw_stats", {}),
        tm_main_position=d.get("tm_main_position", ""),
        tm_other_positions=d.get("tm_other_positions", []),
    )


def _extract_playing_time(player_name: str, tables: dict) -> PlayingTimeStats | None:
    """Parse the FBref playing_time table row for the target player."""
    pt = tables.get("playing_time")
    if pt is None:
        return None
    try:
        norm = _normalize_name(player_name)
        pc = next((c for c in pt.columns if str(c).lower() == "player"), None)
        if pc is None:
            return None
        mask = pt[pc].apply(lambda x: _normalize_name(str(x)) == norm)
        row = pt[mask]
        if row.empty:
            return None
        r = row.iloc[0]

        def _int(key: str) -> int:
            for k in pt.columns:
                if str(k).lower() == key.lower():
                    try:
                        return int(float(r[k]) if str(r[k]) not in ("nan", "None", "") else 0)
                    except (ValueError, TypeError):
                        return 0
            return 0

        def _float(key: str) -> float:
            for k in pt.columns:
                if str(k).lower() == key.lower():
                    try:
                        return float(r[k]) if str(r[k]) not in ("nan", "None", "") else 0.0
                    except (ValueError, TypeError):
                        return 0.0
            return 0.0

        pos_val = ""
        for k in pt.columns:
            if str(k).lower() == "pos":
                pos_val = str(r[k]) if str(r[k]) not in ("nan", "None") else ""
                break

        return PlayingTimeStats(
            pos=pos_val,
            mp=_int("Playing Time_MP"),
            minutes=_int("Playing Time_Min"),
            min_pct=_float("Playing Time_Min%"),
            starts=_int("Starts_Starts"),
            mins_per_start=_int("Starts_Mn/Start"),
            complete_games=_int("Starts_Compl"),
            subs=_int("Subs_Subs"),
            mins_per_sub=_int("Subs_Mn/Sub"),
            unsubbed=_int("Subs_unSub"),
        )
    except Exception as exc:
        log.warning("_extract_playing_time failed: %s", exc)
        return None


def _extract_raw_stats(player_name: str, tables: dict) -> dict:
    """Extract counting stats for the season from standard + shooting tables."""
    result: dict = {}
    norm = _normalize_name(player_name)

    def _get_player_row(df):
        if df is None:
            return None
        pc = next((c for c in df.columns if str(c).lower() == "player"), None)
        if pc is None:
            return None
        mask = df[pc].apply(lambda x: _normalize_name(str(x)) == norm)
        rows = df[mask]
        return rows.iloc[0] if not rows.empty else None

    def _val(row, *keys) -> float:
        for k in keys:
            for col in row.index:
                if str(col).lower() == k.lower():
                    try:
                        v = row[col]
                        return float(v) if str(v) not in ("nan", "None", "") else 0.0
                    except (ValueError, TypeError):
                        return 0.0
        return 0.0

    std_row = _get_player_row(tables.get("standard"))
    if std_row is not None:
        result["goals"]       = _val(std_row, "Performance_Gls")
        result["assists"]     = _val(std_row, "Performance_Ast")
        result["goals_assists"] = _val(std_row, "Performance_G+A")
        result["nineties"]    = _val(std_row, "Playing Time_90s")
        result["yellow_cards"] = _val(std_row, "Performance_CrdY")
        result["red_cards"]   = _val(std_row, "Performance_CrdR")

    sh_row = _get_player_row(tables.get("shooting"))
    if sh_row is not None:
        result["shots"]           = _val(sh_row, "Standard_Sh")
        result["shots_on_target"] = _val(sh_row, "Standard_SoT")
        sot_pct = _val(sh_row, "Standard_SoT%")
        result["sot_pct"] = sot_pct
        goals_np = _val(sh_row, "Standard_G-PK")
        if goals_np:
            result["goals_np"] = goals_np

    misc_row = _get_player_row(tables.get("misc"))
    if misc_row is not None:
        result["fouls_won"]  = _val(misc_row, "Performance_Fld")
        result["fouls"]      = _val(misc_row, "Performance_Fls")
        result["crosses"]    = _val(misc_row, "Performance_Crs")
        result["interceptions"] = _val(misc_row, "Performance_Int")

    return result


def get_pizza_data(player_name: str, season: int, league: str) -> PizzaData | None:
    """Fetch player stats from all available sources and compute percentiles.

    Cache layer:
      1. Read MP from the local FBref JSON cache (fast, no network).
      2. Check SQLite player_cache: valid if TTL not expired AND MP unchanged.
      3. On cache hit → return immediately.
      4. On cache miss → run full pipeline, write result to cache.
    """
    from fastapi import HTTPException

    # ── Step 1: cheap MP read ─────────────────────────────────────────────────
    current_mp = _read_mp_from_cache(player_name, league, season)

    # ── Step 2 & 3: DB cache lookup ───────────────────────────────────────────
    cached = player_db.cache_get(player_name, league, season, current_mp)
    if cached is not None:
        log.info("Cache HIT for %s (%s %s) MP=%d", player_name, league, season, current_mp)
        return _pizza_data_from_dict(cached)

    log.info("Cache MISS for %s (%s %s) MP=%d — recomputing", player_name, league, season, current_mp)

    # ── Step 4: full pipeline ─────────────────────────────────────────────────
    try:
        fetch_result = fetch_all(league, season, _CACHE_DIR)
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Season {season} data not available for {league}. "
                   f"Only completed seasons are supported. ({exc})",
        ) from exc

    tables = add_team_poss(fetch_result.fbref_tables)

    std = tables.get("standard")
    if std is None:
        raise HTTPException(status_code=422, detail=f"No FBref data for {league} {season}")

    pc = next(c for c in std.columns if str(c).lower() == "player")
    all_names = std[pc].dropna().unique().tolist()

    sc_league = fetch_result.sofascore_league_data or {}
    sc_lookup_norm = {_normalize_name(k): v for k, v in sc_league.items()}

    all_player_stats = []
    for n in all_names:
        s = merge_player_stats(n, tables)
        if s:
            s = merge_sources(s, n, fetch_result.understat_data, fetch_result.whoscored_data)
            s = _inject_sc_league_stats(s, n, sc_league, sc_lookup_norm)
            all_player_stats.append(s)

    stats = merge_player_stats(player_name, tables)
    if not stats:
        return None
    stats = merge_sources(stats, player_name, fetch_result.understat_data, fetch_result.whoscored_data)
    stats = _inject_sc_league_stats(stats, player_name, sc_league, sc_lookup_norm)
    stats = _inject_profile_sources(stats, player_name, league=league, season=season)

    pos_raw = stats.get("standard.pos", "DF")
    pos_bucket = map_position(pos_raw)

    # Override position bucket from the canonical player_positions table (set by enrich_positions
    # or by a previous live TM fetch).  TM data is more granular than FBref's broad MF/FW/DF.
    db_pos = player_db.get_position(player_name)
    if db_pos:
        main = db_pos["main_position"]
        if db_pos["source"] == "transfermarkt":
            override_bucket = _TM_POSITION_TO_BUCKET.get(main)
        else:
            override_bucket = main  # already a bucket from FBref
        if override_bucket and override_bucket != "GK":
            pos_bucket = override_bucket
    else:
        # Fall back to live TM data injected by the pipeline
        tm_main = stats.get("transfermarkt.main_position")
        if tm_main:
            override_bucket = _TM_POSITION_TO_BUCKET.get(tm_main)
            if override_bucket and override_bucket != "GK":
                pos_bucket = override_bucket
            # Write the freshly fetched TM position into the DB so future calls use the table
            player_db.upsert_player_positions([{
                "name": player_name,
                "main_position": tm_main,
                "other_positions": stats.get("transfermarkt.other_positions") or [],
                "source": "transfermarkt",
            }])

    # Pre-load canonical position buckets for all peers in this league
    league_positions = player_db.get_positions_for_league(league, season)
    position_overrides: dict[str, str] = {}
    for pname, pdata in league_positions.items():
        main = pdata["main_position"]
        if pdata["source"] == "transfermarkt":
            bucket = _TM_POSITION_TO_BUCKET.get(main)
        else:
            bucket = main  # already a bucket
        if bucket:
            position_overrides[pname] = bucket

    results, missing, peers, similar = compute_percentiles(
        stats, all_player_stats, pos_bucket,
        available_sources=fetch_result.available_sources,
        position_overrides=position_overrides,
    )

    # Enrich peers with TM main/other positions
    for peer in peers:
        pos_data = league_positions.get(peer.name)
        if pos_data and pos_data["source"] == "transfermarkt":
            peer.tm_main_position = pos_data["main_position"]
            peer.tm_other_positions = pos_data["other_positions"]

    # Re-read MP from the freshly loaded data (more reliable than the pre-cache read)
    try:
        mp_col = next((c for c in std.columns if "playing time_mp" in str(c).lower()), None)
        if mp_col:
            norm_target = _normalize_name(player_name)
            mp_row = std[std[pc].apply(lambda x: _normalize_name(str(x)) == norm_target)]
            fresh_mp = int(mp_row[mp_col].iloc[0]) if not mp_row.empty else current_mp
        else:
            fresh_mp = current_mp
    except Exception:
        fresh_mp = current_mp

    season_label = f"{season}-{str(season + 1)[-2:]}"
    _raw = _extract_raw_stats(player_name, tables)
    # Enrich with multi-source stats
    def _ms(key: str):
        v = stats.get(key)
        return float(v) if v is not None else None
    for dest, src in [
        ("xg",              "understat.xG"),
        ("npxg",            "understat.npxG"),
        ("xa",              "sofascore.expectedAssists"),
        ("rating",          "sofascore.rating"),
        ("index_overall",   "ovo.index_overall"),
        ("index_offensive", "ovo.index_offensive"),
        ("index_defensive", "ovo.index_defensive"),
    ]:
        v = _ms(src)
        if v is not None:
            _raw[dest] = v

    pizza = PizzaData(
        player=player_name,
        position=pos_bucket,
        season=season_label,
        league=league,
        metrics=results,
        missing_metrics=missing,
        data_sources=fetch_result.available_sources,
        data_freshness=fetch_result.data_freshness,
        peers=peers,
        similar_players=similar,
        playing_time=_extract_playing_time(player_name, tables),
        raw_stats=_raw,
        tm_main_position=stats.get("transfermarkt.main_position") or "",
        tm_other_positions=stats.get("transfermarkt.other_positions") or [],
    )

    # ── Write to cache ────────────────────────────────────────────────────────
    try:
        player_db.cache_set(player_name, league, season, fresh_mp, pizza.model_dump())
    except Exception as exc:
        log.warning("cache_set failed (non-fatal): %s", exc)

    return pizza

