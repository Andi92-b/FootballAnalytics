"""
clusters.py — FastAPI router for the cluster-explorer endpoints.

GET  /api/clusters         Return PCA-projected player scatter data + centroid profiles.
POST /api/clusters/rebuild Re-run build_roles.py with custom k-means parameters.
GET  /api/clusters/info    Parameter / feature documentation.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend import db

router = APIRouter(prefix="/api")

# Feature ordering and human-readable labels
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

FEATURE_META: dict[str, dict] = {
    "goals_per90":   {"label": "Goals/90",          "desc": "Non-penalty goals per 90 minutes"},
    "assists_per90": {"label": "Assists/90",         "desc": "Goal assists per 90 minutes"},
    "shots_per90":   {"label": "Shots/90",           "desc": "Total shots per 90 minutes"},
    "sot_pct":       {"label": "Shots on Target %",  "desc": "Fraction of shots on target (0–1)"},
    "int_per90":     {"label": "Interceptions/90",   "desc": "Interceptions per 90 minutes"},
    "tkl_per90":     {"label": "Tackles Won/90",     "desc": "Tackles won per 90 minutes"},
    "fld_per90":     {"label": "Fouls Drawn/90",     "desc": "Fouls drawn per 90 minutes"},
    "crs_per90":     {"label": "Crosses/90",         "desc": "Crosses attempted per 90 minutes"},
}

_ROOT = Path(__file__).parents[3]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/clusters
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/clusters")
async def get_clusters(league: str = Query(default="")):
    """
    Return PCA scatter coordinates for all clustered players, plus per-cluster
    centroid profiles and explained variance.

    Optional ?league=ENG-Premier+League filters to one league.
    """
    rows = db.get_all_roles()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No cluster data found. Run build_roles.py first.",
        )

    if league:
        rows = [r for r in rows if r["league"] == league]
        if not rows:
            raise HTTPException(status_code=404, detail=f"No roles for league: {league!r}")

    # Build feature matrix (preserve key order)
    features_matrix = np.array(
        [[json.loads(r["features_json"]).get(k, 0.0) for k in FEATURE_KEYS] for r in rows],
        dtype=float,
    )
    features_matrix = np.nan_to_num(features_matrix)

    # PCA projection to 2D
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features_matrix)

    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)

    variance_explained = [round(float(v), 4) for v in pca.explained_variance_ratio_]

    # Per-player output
    players_out = []
    for i, row in enumerate(rows):
        feats = json.loads(row["features_json"])
        players_out.append({
            "name": row["name"],
            "team": row["team"] or "",
            "league": row["league"],
            "season": row["season"],
            "role": row["role_label"],
            "cluster_id": row["cluster_id"],
            "minutes": row.get("minutes", 0),
            "x": round(float(X_pca[i, 0]), 4),
            "y": round(float(X_pca[i, 1]), 4),
            "features": {k: round(float(feats.get(k, 0.0)), 3) for k in FEATURE_KEYS},
        })

    # Per-cluster centroid profiles in PCA space + feature means
    cluster_groups: dict[tuple, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        cluster_groups[(row["cluster_id"], row["role_label"])].append(i)

    centroids_out = []
    for (cid, role), idxs in sorted(cluster_groups.items()):
        feat_mean = {}
        for k in FEATURE_KEYS:
            vals = [json.loads(rows[i]["features_json"]).get(k, 0.0) for i in idxs]
            feat_mean[k] = round(float(np.mean(vals)), 3)

        # Top players by minutes
        top = sorted(
            [{"name": rows[i]["name"], "team": rows[i]["team"] or "",
              "minutes": rows[i].get("minutes", 0)} for i in idxs],
            key=lambda p: p["minutes"],
            reverse=True,
        )[:8]

        centroids_out.append({
            "cluster_id": cid,
            "role": role,
            "count": len(idxs),
            "x": round(float(np.mean(X_pca[idxs, 0])), 4),
            "y": round(float(np.mean(X_pca[idxs, 1])), 4),
            "features_mean": feat_mean,
            "top_players": top,
        })

    return {
        "players": players_out,
        "centroids": centroids_out,
        "variance_explained": variance_explained,
        "feature_meta": FEATURE_META,
        "total": len(rows),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/clusters/info
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/clusters/info")
async def get_cluster_info():
    """Return documentation: feature definitions, default parameter values."""
    return {
        "algorithm": {
            "name": "K-Means",
            "library": "scikit-learn",
            "normalization": "StandardScaler (zero mean, unit variance per feature)",
            "init": "k-means++, n_init=15, max_iter=500",
        },
        "parameters": {
            "n_clusters": {
                "default": 9,
                "range": [3, 20],
                "desc": "Number of clusters — each becomes a tactical role label",
            },
            "min_90s": {
                "default": 5.0,
                "range": [1.0, 30.0],
                "desc": "Minimum 90-minute appearances required to include a player",
            },
            "seed": {
                "default": 42,
                "range": None,
                "desc": "Random seed for k-means reproducibility",
            },
        },
        "features": FEATURE_META,
        "data_sources": [
            "FBref Standard Stats (goals, assists, 90s)",
            "FBref Shooting (shots, SoT%)",
            "FBref Misc Stats (interceptions, tackles, fouls drawn, crosses)",
        ],
        "leagues": [
            "ENG-Premier League (seasons 2024, 2025)",
            "GER-Bundesliga (seasons 2024, 2025)",
        ],
        "role_naming": (
            "Role labels are assigned by inspecting each cluster centroid's "
            "feature values with ordered threshold rules (see build_roles.py → auto_name())."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/clusters/rebuild
# ─────────────────────────────────────────────────────────────────────────────

class RebuildParams(BaseModel):
    n_clusters: int = 9
    min_90s: float = 5.0
    seed: int = 42


@router.post("/clusters/rebuild")
async def rebuild_clusters(params: RebuildParams):
    """
    Re-run build_roles.py with custom parameters.
    Rewrites the player_roles table — this takes ~5 s.
    """
    if not (3 <= params.n_clusters <= 20):
        raise HTTPException(status_code=422, detail="n_clusters must be between 3 and 20")
    if not (1.0 <= params.min_90s <= 30.0):
        raise HTTPException(status_code=422, detail="min_90s must be between 1.0 and 30.0")

    result = subprocess.run(
        [
            sys.executable, "-m", "backend.scripts.build_roles",
            "--n-clusters", str(params.n_clusters),
            "--min-90s",   str(params.min_90s),
            "--seed",      str(params.seed),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"build_roles failed:\n{result.stderr[:1000]}",
        )

    return {"ok": True, "output": result.stdout}
