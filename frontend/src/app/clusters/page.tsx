"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";

const API = "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────────────────────

interface PlayerPoint {
  name: string;
  team: string;
  league: string;
  season: number;
  role: string;
  cluster_id: number;
  minutes: number;
  x: number;
  y: number;
  features: Record<string, number>;
}

interface Centroid {
  cluster_id: number;
  role: string;
  count: number;
  x: number;
  y: number;
  features_mean: Record<string, number>;
  top_players: { name: string; team: string; minutes: number }[];
}

interface ClusterData {
  players: PlayerPoint[];
  centroids: Centroid[];
  variance_explained: number[];
  feature_meta: Record<string, { label: string; desc: string }>;
  total: number;
}

// ── Colour palette ───────────────────────────────────────────────────────────

const ROLE_HEX: Record<string, string> = {
  "Goal Scorer":           "#f59e0b",
  "Wide Attacker":         "#10b981",
  "Dynamic Winger":        "#14b8a6",
  "Wide Creator":          "#06b6d4",
  "Winger":                "#22c55e",
  "Attacking Fullback":    "#0ea5e9",
  "Fullback":              "#3b82f6",
  "Centre-Back":           "#6366f1",
  "Ball-playing Defender": "#8b5cf6",
  "Defensive Midfielder":  "#a855f7",
  "Deep-lying Playmaker":  "#d946ef",
};

const DEFAULT_HEX = "#9ca3af";

function roleHex(role: string): string {
  return ROLE_HEX[role] ?? DEFAULT_HEX;
}

// ── Scatter plot ─────────────────────────────────────────────────────────────

const W = 580, H = 440, PAD = 46;

function ScatterPlot({
  players,
  centroids,
  variance,
  selectedCluster,
  onSelectCluster,
}: {
  players: PlayerPoint[];
  centroids: Centroid[];
  variance: number[];
  selectedCluster: number | null;
  onSelectCluster: (id: number | null) => void;
}) {
  const [tooltip, setTooltip] = useState<{ p: PlayerPoint; px: number; py: number } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const xs = players.map((p) => p.x);
  const ys = players.map((p) => p.y);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const xPad = (xMax - xMin) * 0.06, yPad = (yMax - yMin) * 0.06;
  const xl = xMin - xPad, xr = xMax + xPad;
  const yb = yMin - yPad, yt = yMax + yPad;

  const tx = (x: number) => PAD + ((x - xl) / (xr - xl)) * (W - 2 * PAD);
  const ty = (y: number) => H - PAD - ((y - yb) / (yt - yb)) * (H - 2 * PAD);

  const handleMouseMove = (e: React.MouseEvent, p: PlayerPoint) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTooltip({ p, px: e.clientX - rect.left + 10, py: e.clientY - rect.top - 28 });
  };

  return (
    <div className="relative select-none">
      <svg
        ref={svgRef}
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="rounded-xl border border-gray-100 bg-gray-50"
      >
        {/* Axis lines */}
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#e5e7eb" strokeWidth={1} />
        <line x1={PAD} y1={PAD}     x2={PAD}      y2={H - PAD} stroke="#e5e7eb" strokeWidth={1} />

        {/* Axis labels */}
        <text x={W / 2} y={H - 6} textAnchor="middle" fontSize={11} fill="#9ca3af">
          PC 1 — {(variance[0] * 100).toFixed(1)}% variance explained
        </text>
        <text
          x={12} y={H / 2}
          textAnchor="middle" fontSize={11} fill="#9ca3af"
          transform={`rotate(-90, 12, ${H / 2})`}
        >
          PC 2 — {(variance[1] * 100).toFixed(1)}%
        </text>

        {/* Player dots */}
        {players.map((p, i) => {
          const dim = selectedCluster !== null && selectedCluster !== p.cluster_id;
          return (
            <circle
              key={i}
              cx={tx(p.x)}
              cy={ty(p.y)}
              r={dim ? 3 : 4.5}
              fill={roleHex(p.role)}
              opacity={dim ? 0.15 : 0.75}
              stroke={dim ? "none" : "rgba(255,255,255,0.4)"}
              strokeWidth={0.8}
              style={{ cursor: "pointer", transition: "opacity 0.15s" }}
              onMouseMove={(e) => handleMouseMove(e, p)}
              onMouseLeave={() => setTooltip(null)}
              onClick={() =>
                onSelectCluster(selectedCluster === p.cluster_id ? null : p.cluster_id)
              }
            />
          );
        })}

        {/* Centroid labels */}
        {centroids.map((c) => {
          const dim = selectedCluster !== null && selectedCluster !== c.cluster_id;
          return (
            <g key={c.cluster_id} style={{ cursor: "pointer" }}
               onClick={() => onSelectCluster(selectedCluster === c.cluster_id ? null : c.cluster_id)}>
              <text
                x={tx(c.x)} y={ty(c.y) - 9}
                textAnchor="middle" fontSize={10} fontWeight="700"
                fill={roleHex(c.role)}
                opacity={dim ? 0.3 : 1}
                style={{ transition: "opacity 0.15s", userSelect: "none" }}
              >
                {c.role}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Hover tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-md text-xs"
          style={{ left: tooltip.px, top: tooltip.py }}
        >
          <p className="font-semibold text-gray-900">{tooltip.p.name}</p>
          <p className="text-gray-500">{tooltip.p.team} · {tooltip.p.league.replace(/^[A-Z]+-/, "")}</p>
          <p className="mt-0.5 font-medium" style={{ color: roleHex(tooltip.p.role) }}>
            {tooltip.p.role}
          </p>
          <p className="text-gray-400 mt-0.5">{tooltip.p.minutes} min</p>
        </div>
      )}
    </div>
  );
}

// ── Centroid feature bars ─────────────────────────────────────────────────────

const FEATURE_KEYS = [
  "goals_per90", "assists_per90", "shots_per90", "sot_pct",
  "int_per90", "tkl_per90", "fld_per90", "crs_per90",
];

function FeatureBars({
  centroid,
  maxValues,
  featureMeta,
}: {
  centroid: Centroid;
  maxValues: Record<string, number>;
  featureMeta: Record<string, { label: string; desc: string }>;
}) {
  const color = roleHex(centroid.role);
  return (
    <div className="space-y-1.5">
      {FEATURE_KEYS.map((k) => {
        const val = centroid.features_mean[k] ?? 0;
        const max = maxValues[k] ?? 1;
        const pct = Math.min(100, (val / max) * 100);
        const label = featureMeta[k]?.label ?? k;
        return (
          <div key={k} className="flex items-center gap-2">
            <span className="w-28 shrink-0 text-right text-[11px] text-gray-500 leading-tight">
              {label}
            </span>
            <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{ width: `${pct}%`, backgroundColor: color }}
              />
            </div>
            <span className="w-9 text-[11px] text-gray-500 tabular-nums">{val.toFixed(2)}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Cluster card (sidebar) ────────────────────────────────────────────────────

function ClusterCard({
  centroid,
  maxValues,
  featureMeta,
  active,
  onClick,
}: {
  centroid: Centroid;
  maxValues: Record<string, number>;
  featureMeta: Record<string, { label: string; desc: string }>;
  active: boolean;
  onClick: () => void;
}) {
  const color = roleHex(centroid.role);
  return (
    <div
      className={`rounded-xl border p-3 cursor-pointer transition-all ${
        active ? "border-current shadow-sm" : "border-gray-200 hover:border-gray-300"
      }`}
      style={{ borderColor: active ? color : undefined }}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold" style={{ color }}>{centroid.role}</span>
        <span className="text-xs text-gray-400">{centroid.count} players</span>
      </div>

      {active && (
        <>
          <FeatureBars centroid={centroid} maxValues={maxValues} featureMeta={featureMeta} />
          <div className="mt-3 pt-2.5 border-t border-gray-100">
            <p className="text-[10px] uppercase tracking-wide text-gray-400 mb-1.5">Top by minutes</p>
            <div className="flex flex-wrap gap-1">
              {centroid.top_players.map((p) => (
                <span
                  key={p.name}
                  className="text-xs rounded-full bg-gray-100 px-2 py-0.5 text-gray-700"
                  title={`${p.team} — ${p.minutes} min`}
                >
                  {p.name}
                </span>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Algorithm docs ────────────────────────────────────────────────────────────

function AlgorithmDocs({ info }: { info: Record<string, unknown> | null }) {
  const [open, setOpen] = useState(false);
  if (!info) return null;
  const algo = info.algorithm as Record<string, string>;
  const features = info.features as Record<string, { label: string; desc: string }>;
  return (
    <div className="mt-6 rounded-xl border border-gray-200">
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-xl"
        onClick={() => setOpen((o) => !o)}
      >
        <span>How it works</span>
        <span className="text-gray-400 text-xs">{open ? "▲ collapse" : "▼ expand"}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-4 text-sm text-gray-600">
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div>
              <p className="font-medium text-gray-800 mb-1">Algorithm</p>
              <ul className="space-y-0.5 text-xs">
                <li><span className="text-gray-400">Method:</span> {algo.name}</li>
                <li><span className="text-gray-400">Library:</span> {algo.library}</li>
                <li><span className="text-gray-400">Normalisation:</span> {algo.normalization}</li>
                <li><span className="text-gray-400">Init:</span> {algo.init}</li>
              </ul>
            </div>
            <div>
              <p className="font-medium text-gray-800 mb-1">Data Sources</p>
              <ul className="space-y-0.5 text-xs">
                {(info.data_sources as string[]).map((s, i) => (
                  <li key={i} className="text-gray-600">• {s}</li>
                ))}
              </ul>
            </div>
          </div>
          <div>
            <p className="font-medium text-gray-800 mb-2">Input Features (8)</p>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1">
              {FEATURE_KEYS.map((k) => (
                <div key={k} className="flex gap-2 text-xs">
                  <span className="font-mono text-indigo-600 shrink-0 w-28">{features[k]?.label}</span>
                  <span className="text-gray-500">{features[k]?.desc}</span>
                </div>
              ))}
            </div>
          </div>
          <p className="text-xs text-gray-500">
            <span className="font-medium text-gray-700">Role naming:</span>{" "}
            {info.role_naming as string}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Parameter panel ───────────────────────────────────────────────────────────

function ParameterPanel({
  onRebuilt,
}: {
  onRebuilt: () => void;
}) {
  const [nClusters, setNClusters] = useState(9);
  const [minNineties, setMinNineties] = useState(5);
  const [seed, setSeed] = useState(42);
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [output, setOutput] = useState("");
  const [open, setOpen] = useState(false);

  async function handleRebuild() {
    if (!window.confirm(
      `Re-run clustering with ${nClusters} clusters and min_90s=${minNineties}?\n\nThis will rewrite the player_roles table (~5 seconds).`
    )) return;

    setStatus("running");
    setOutput("");
    try {
      const res = await fetch(`${API}/api/clusters/rebuild`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n_clusters: nClusters, min_90s: minNineties, seed }),
      });
      const j = await res.json();
      if (!res.ok) {
        setStatus("error");
        setOutput(j.detail ?? "Unknown error");
      } else {
        setStatus("done");
        setOutput(j.output ?? "");
        onRebuilt();
      }
    } catch (e) {
      setStatus("error");
      setOutput(String(e));
    }
  }

  return (
    <div className="mt-4 rounded-xl border border-gray-200">
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-xl"
        onClick={() => setOpen((o) => !o)}
      >
        <span>Clustering parameters</span>
        <span className="text-gray-400 text-xs">{open ? "▲ collapse" : "▼ expand"}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                N Clusters <span className="text-indigo-500 font-mono">{nClusters}</span>
              </label>
              <input
                type="range" min={3} max={20} step={1}
                value={nClusters}
                onChange={(e) => setNClusters(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
              <div className="flex justify-between text-[10px] text-gray-400"><span>3</span><span>20</span></div>
              <p className="text-[11px] text-gray-400 mt-1">Number of tactical role groups</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Min 90s <span className="text-indigo-500 font-mono">{minNineties}</span>
              </label>
              <input
                type="range" min={1} max={20} step={1}
                value={minNineties}
                onChange={(e) => setMinNineties(Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
              <div className="flex justify-between text-[10px] text-gray-400"><span>1</span><span>20</span></div>
              <p className="text-[11px] text-gray-400 mt-1">Minimum 90-minute appearances</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Random Seed
              </label>
              <input
                type="number" min={0} max={9999}
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="w-full border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              <p className="text-[11px] text-gray-400 mt-1">Controls k-means initialisation</p>
            </div>
          </div>

          <button
            onClick={handleRebuild}
            disabled={status === "running"}
            className="bg-indigo-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {status === "running" ? "Running…" : "Re-run Clustering"}
          </button>

          {output && (
            <pre className={`text-xs rounded-lg p-3 font-mono whitespace-pre-wrap max-h-48 overflow-y-auto ${
              status === "error" ? "bg-red-50 text-red-700" : "bg-gray-50 text-gray-700"
            }`}>
              {output}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ClustersPage() {
  const [data, setData] = useState<ClusterData | null>(null);
  const [info, setInfo] = useState<Record<string, unknown> | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [clRes, infoRes] = await Promise.all([
        fetch(`${API}/api/clusters`),
        fetch(`${API}/api/clusters/info`),
      ]);
      if (!clRes.ok) throw new Error(`Clusters API error ${clRes.status}`);
      setData(await clRes.json());
      if (infoRes.ok) setInfo(await infoRes.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Compute per-feature max across all centroids (for normalising bars)
  const maxValues = data
    ? Object.fromEntries(
        FEATURE_KEYS.map((k) => [k, Math.max(...data.centroids.map((c) => c.features_mean[k] ?? 0)) || 1])
      )
    : {};

  const activeCentroid = data?.centroids.find((c) => c.cluster_id === selectedCluster) ?? null;

  return (
    <main className="min-h-screen bg-white py-10 px-6">
      {/* Header */}
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-1">
          <Link href="/" className="text-sm text-gray-400 hover:text-gray-700 transition-colors">
            ← Football Analytics
          </Link>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Cluster Explorer</h1>
        <p className="text-sm text-gray-500 mb-8">
          K-means tactical role clustering · {data?.total ?? "…"} players ·{" "}
          {data ? `${data.centroids.length} roles` : "loading"}
        </p>

        {isLoading && (
          <p className="text-gray-400 text-sm">Loading cluster data…</p>
        )}
        {error && (
          <p className="text-red-600 text-sm bg-red-50 rounded-lg px-4 py-3">{error}</p>
        )}

        {data && (
          <div className="flex gap-8 items-start">
            {/* Left: scatter + docs + params */}
            <div className="shrink-0">
              <ScatterPlot
                players={data.players}
                centroids={data.centroids}
                variance={data.variance_explained}
                selectedCluster={selectedCluster}
                onSelectCluster={setSelectedCluster}
              />
              <p className="text-[11px] text-gray-400 mt-1.5 ml-1">
                Click any dot or label to highlight a role.{" "}
                {selectedCluster !== null && (
                  <button
                    className="text-indigo-500 hover:underline"
                    onClick={() => setSelectedCluster(null)}
                  >
                    Clear selection
                  </button>
                )}
              </p>
              <AlgorithmDocs info={info} />
              <ParameterPanel onRebuilt={loadData} />
            </div>

            {/* Right: cluster cards */}
            <div className="flex-1 min-w-0">
              <p className="text-xs uppercase tracking-wide text-gray-400 mb-3">
                {selectedCluster !== null
                  ? `${activeCentroid?.count} players · click card again to deselect`
                  : "Click a role to see its feature profile"}
              </p>
              <div className="space-y-2">
                {data.centroids.map((c) => (
                  <ClusterCard
                    key={c.cluster_id}
                    centroid={c}
                    maxValues={maxValues}
                    featureMeta={data.feature_meta}
                    active={selectedCluster === c.cluster_id}
                    onClick={() =>
                      setSelectedCluster(selectedCluster === c.cluster_id ? null : c.cluster_id)
                    }
                  />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
