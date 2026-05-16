"""
build_roles.py — Cluster Premier League (and Bundesliga) players into tactical roles.

Uses k-means on 8 per-90 FBref features from the local cache.
Writes results into .cache/players.db → player_roles table.

Run from repo root:
  .venv/bin/python -m backend.scripts.build_roles [OPTIONS]

Options:
  --n-clusters INT    Number of k-means clusters (default: 9, range 3–20)
  --min-90s   FLOAT   Minimum 90-minute appearances to qualify (default: 5.0)
  --seed      INT     Random seed for k-means reproducibility (default: 42)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

CACHE_DIR = ROOT / ".cache" / "fbref"
DB_PATH = ROOT / ".cache" / "players.db"

# League configs: (display name, cache folder slug, season start-year)
CONFIGS = [
    ("ENG-Premier League", "ENG_Premier_League", 2025),
    ("ENG-Premier League", "ENG_Premier_League", 2024),
    ("GER-Bundesliga", "GER_Bundesliga", 2025),
    ("GER-Bundesliga", "GER_Bundesliga", 2024),
]

MIN_90S = 5.0  # minimum qualifying full games

FEATURE_KEYS = [
    "goals_per90",
    "assists_per90",
    "shots_per90",
    "sot_pct",
    "int_per90",
    "tkl_per90",
    "fld_per90",
    "crs_per90",
]

N_CLUSTERS = 9


def _fv(row: dict, key: str, default: float = 0.0) -> float:
    try:
        v = row.get(key)
        return float(v) if v not in (None, "", "N/A", "nan") else default
    except (ValueError, TypeError):
        return default


def load_players(league: str, slug: str, season: int) -> list[dict]:
    """Load and join FBref tables for one league / season."""
    d = CACHE_DIR / slug / str(season)
    if not d.exists():
        print(f"  [skip] {d} not found")
        return []

    std = json.loads((d / "standard.json").read_text())
    sh_raw = json.loads((d / "shooting.json").read_text()) if (d / "shooting.json").exists() else []
    misc_raw = json.loads((d / "misc.json").read_text()) if (d / "misc.json").exists() else []

    sh_by = {(r["player"], r["team"]): r for r in sh_raw}
    misc_by = {(r["player"], r["team"]): r for r in misc_raw}

    players = []
    for row in std:
        pos = str(row.get("pos") or "")
        # Exclude pure GKs
        if pos.strip() == "GK":
            continue

        nineties = _fv(row, "Playing Time_90s")
        if nineties < MIN_90S:
            continue

        key = (row["player"], row.get("team", ""))
        sh = sh_by.get(key, {})
        misc = misc_by.get(key, {})

        int_ = _fv(misc, "Performance_Int")
        tkl_ = _fv(misc, "Performance_TklW")
        fld_ = _fv(misc, "Performance_Fld")
        crs_ = _fv(misc, "Performance_Crs")

        players.append({
            "name": row["player"],
            "team": row.get("team", ""),
            "league": league,
            "season": season,
            "pos": pos,
            "minutes": int(_fv(row, "Playing Time_Min")),
            "goals_per90": _fv(row, "Per 90 Minutes_Gls"),
            "assists_per90": _fv(row, "Per 90 Minutes_Ast"),
            "shots_per90": _fv(sh, "Standard_Sh/90"),
            "sot_pct": _fv(sh, "Standard_SoT%") / 100.0,
            "int_per90": int_ / nineties if nineties > 0 else 0.0,
            "tkl_per90": tkl_ / nineties if nineties > 0 else 0.0,
            "fld_per90": fld_ / nineties if nineties > 0 else 0.0,
            "crs_per90": crs_ / nineties if nineties > 0 else 0.0,
        })

    return players


def auto_name(centroid: np.ndarray) -> tuple[str, str]:
    """Assign a role label + description from a centroid in original feature space.

    Thresholds are calibrated against EPL 2024/25 cluster centroids.
    Order matters — earlier rules take priority.
    """
    goals, assists, shots, sot_pct, ints, tkl, fld, crs = centroid
    dfn = ints + tkl

    # 1. Strikers: very high goals + shots
    if goals >= 0.4:
        return ("Goal Scorer",
                "A constant goal threat — prolific in front of goal")

    # 2. Passive defenders: minimal attack output
    if goals < 0.03 and shots < 0.5:
        return ("Ball-playing Defender",
                "A composed and dependable presence at the back; comfortable in possession")

    # 3. Wide attacker with high crossing volume (Martinelli / Trossard profile)
    if crs >= 3.5 and shots >= 1.5:
        return ("Wide Attacker",
                "Direct and dangerous from wide; delivers crosses and threatens goal")

    # 4. Extreme crossers with moderate shots (pure crossing wide player)
    if crs >= 4.5:
        return ("Wide Creator",
                "Creates chances from wide with an exceptional crossing delivery")

    # 5. Dynamic winger (Saka profile: goals + shots + foul drawing + some crosses)
    if shots >= 1.8 and fld >= 1.8 and crs >= 1.5:
        return ("Dynamic Winger",
                "Takes players on from wide; threatens goal and draws fouls in abundance")

    # 6a. Wide attacker with creative output (assists + crosses + shots)
    if shots >= 1.7 and assists >= 0.25 and crs >= 2.5:
        return ("Wide Attacker",
                "Combines goals, assists, and crosses — a threat from wide in every sense")

    # 6b. Winger / attacking midfielder (Sancho / Rogers profile)
    if shots >= 1.7:
        return ("Winger",
                "Provides width and a direct goal threat from attacking positions")

    # 7. Defensive fullbacks: solid defensive output + wide delivery, minimal goals
    if dfn >= 2.8 and crs >= 1.3 and goals < 0.07:
        return ("Fullback",
                "Dependable on both sides of the ball with regular wide contributions")

    # 8. Attacking fullbacks: balanced attacking + defensive + wide contributions
    if crs >= 1.5 and dfn >= 1.2 and shots >= 0.85:
        return ("Attacking Fullback",
                "Combines defensive duties with frequent and dangerous attacking overlaps")

    # 9. Defensive midfielders / ball-winners
    if dfn >= 2.5:
        return ("Defensive Midfielder",
                "Shields the backline and wins the ball in central areas")

    # 10. Centre-backs: moderate defense, minimal attack
    if dfn >= 1.5 and goals < 0.1 and shots < 0.7:
        return ("Centre-Back",
                "Marshals the defence; wins headers, tackles, and blocks")

    return ("Deep-lying Playmaker",
            "Controls the tempo from deep; the fulcrum between defence and attack")


def cluster_and_store(
    all_players: list[dict],
    n_clusters: int = N_CLUSTERS,
    seed: int = 42,
) -> None:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    if not all_players:
        print("No players to cluster.")
        return

    X = np.array([[p[k] for k in FEATURE_KEYS] for p in all_players], dtype=float)
    X = np.nan_to_num(X)

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    km = KMeans(n_clusters=n_clusters, random_state=seed, n_init=15, max_iter=500)
    labels = km.fit_predict(Xs)

    centroids_orig = scaler.inverse_transform(km.cluster_centers_)
    role_map: dict[int, tuple[str, str]] = {
        i: auto_name(centroids_orig[i]) for i in range(n_clusters)
    }

    print(f"\nCluster assignments ({n_clusters} clusters, {len(all_players)} players):")
    for cid, (label, _) in sorted(role_map.items()):
        members = [p["name"] for p, lbl in zip(all_players, labels) if lbl == cid]
        print(f"  [{cid}] {label:30s}  {len(members):3d} players — {members[:4]}")

    # ── write to DB ──────────────────────────────────────────────────────────
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_roles (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                league        TEXT NOT NULL,
                season        INTEGER NOT NULL,
                cluster_id    INTEGER NOT NULL,
                role_label    TEXT NOT NULL,
                role_desc     TEXT NOT NULL DEFAULT '',
                features_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(name, league, season)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_roles_name ON player_roles(name)"
        )

        rows = []
        for player, lbl in zip(all_players, labels):
            cid = int(lbl)
            role_label, role_desc = role_map[cid]
            rows.append((
                player["name"],
                player["league"],
                player["season"],
                cid,
                role_label,
                role_desc,
                json.dumps({k: round(float(player[k]), 4) for k in FEATURE_KEYS}),
            ))

        conn.executemany(
            """
            INSERT INTO player_roles (name, league, season, cluster_id, role_label, role_desc, features_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name, league, season) DO UPDATE SET
                cluster_id    = excluded.cluster_id,
                role_label    = excluded.role_label,
                role_desc     = excluded.role_desc,
                features_json = excluded.features_json
            """,
            rows,
        )

    print(f"\n✓  Stored {len(rows)} role assignments in player_roles table")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cluster football players into tactical roles.")
    parser.add_argument("--n-clusters", type=int, default=N_CLUSTERS,
                        help="Number of k-means clusters (default: %(default)s, range 3–20)")
    parser.add_argument("--min-90s", type=float, default=MIN_90S,
                        help="Minimum 90-minute appearances to qualify (default: %(default)s)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for k-means reproducibility (default: %(default)s)")
    args = parser.parse_args()

    if not (3 <= args.n_clusters <= 20):
        parser.error("--n-clusters must be between 3 and 20")
    if not (1.0 <= args.min_90s <= 30.0):
        parser.error("--min-90s must be between 1.0 and 30.0")

    # Apply runtime min_90s override
    global MIN_90S
    MIN_90S = args.min_90s

    all_players: list[dict] = []
    for league, slug, season in CONFIGS:
        print(f"Loading {league} {season}...")
        players = load_players(league, slug, season)
        print(f"  → {len(players)} qualifying players")
        all_players.extend(players)

    if not all_players:
        print("No data found. Make sure FBref cache exists under .cache/fbref/")
        return

    # Deduplicate: one row per (name, league) keeping the latest season
    seen: dict[tuple[str, str], dict] = {}
    for p in all_players:
        key = (p["name"], p["league"])
        if key not in seen or p["season"] > seen[key]["season"]:
            seen[key] = p
    deduped = list(seen.values())
    print(f"\nUnique players (latest season per league): {len(deduped)}")

    cluster_and_store(deduped, n_clusters=args.n_clusters, seed=args.seed)


if __name__ == "__main__":
    main()
