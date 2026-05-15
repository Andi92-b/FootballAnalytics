"use client";

import { useState } from "react";

export interface SeasonDataPoint {
  season: number;
  season_label: string;
  league: string;
  overall_score: number;
  category_scores: Record<string, number>;
  raw_kpis: Record<string, number>;
}

interface Props {
  history: SeasonDataPoint[];
  position: string;
}

type Tab = "scores" | "output" | "time";

// ── Score trend line definitions ─────────────────────────────────────────────
const SCORE_LINES = [
  { key: "overall",     label: "Overall",     color: "#6b7280" },
  { key: "Defence",     label: "Defence",     color: "#3b82f6" },
  { key: "Possession",  label: "Possession",  color: "#14b8a6" },
  { key: "Progression", label: "Progression", color: "#a855f7" },
  { key: "Attack",      label: "Attack",      color: "#f59e0b" },
];

function getScore(pt: SeasonDataPoint, key: string): number | undefined {
  if (key === "overall") return pt.overall_score;
  return pt.category_scores[key];
}

// ── Mini sparkline ────────────────────────────────────────────────────────────
function MiniSparkline({ values, color }: { values: (number | undefined)[]; color: string }) {
  const valid = values.filter((v): v is number => v !== undefined && !isNaN(v));
  const W = 100, H = 28;
  if (valid.length === 0) return <div style={{ height: H }} />;
  if (valid.length === 1) {
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: H }}>
        <circle cx={W / 2} cy={H / 2} r={3} fill={color} />
      </svg>
    );
  }
  const min = Math.min(...valid);
  const max = Math.max(...valid);
  const range = max - min || 1;
  const n = values.length;
  const coords = values.map((v, i) => ({
    x: n === 1 ? W / 2 : (i / (n - 1)) * W,
    y: v !== undefined && !isNaN(v) ? H - 2 - ((v - min) / range) * (H - 6) : null,
  }));
  const validCoords = coords.filter((c): c is { x: number; y: number } => c.y !== null);
  const d = validCoords
    .map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: H }}>
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
      {validCoords.map((c, i) => (
        <circle key={i} cx={c.x} cy={c.y} r={2.5} fill={color} />
      ))}
    </svg>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────────
interface StatCardDef {
  key: string;
  label: string;
  color: string;
  fmt?: (v: number) => string;
  getValue: (pt: SeasonDataPoint) => number | undefined;
}

function StatCard({ def, history }: { def: StatCardDef; history: SeasonDataPoint[] }) {
  const values = history.map(def.getValue);
  const valid = values.filter((v): v is number => v !== undefined && !isNaN(v));
  if (valid.length === 0) return null;
  const latest = values[values.length - 1];
  const prev = values[values.length - 2];
  const delta =
    latest !== undefined &&
    !isNaN(latest) &&
    prev !== undefined &&
    !isNaN(prev)
      ? latest - prev
      : null;
  const fmtVal = def.fmt ?? ((v: number) => String(Math.round(v)));
  const fmtDelta =
    def.fmt ?? ((v: number) => (Math.abs(v) >= 10 ? String(Math.round(v)) : v.toFixed(1)));

  return (
    <div className="border border-gray-100 rounded-lg p-3 flex flex-col gap-1.5 bg-white min-w-0">
      <span className="text-[9px] text-gray-400 uppercase tracking-wide font-medium leading-none">
        {def.label}
      </span>
      <div className="flex items-end justify-between gap-1">
        <span className="text-xl font-bold text-gray-900 tabular-nums leading-none">
          {latest !== undefined ? fmtVal(latest) : "–"}
        </span>
        {delta !== null && Math.abs(delta) > 0.05 && (
          <span
            className={`text-[10px] font-semibold tabular-nums mb-0.5 ${
              delta > 0 ? "text-green-500" : "text-red-400"
            }`}
          >
            {delta > 0 ? "+" : ""}
            {fmtDelta(delta)}
          </span>
        )}
      </div>
      <MiniSparkline values={values} color={def.color} />
    </div>
  );
}

const OUTPUT_STATS: StatCardDef[] = [
  {
    key: "goals",
    label: "Goals",
    color: "#3b82f6",
    getValue: (pt) => pt.raw_kpis.goals,
  },
  {
    key: "xg",
    label: "xG",
    color: "#93c5fd",
    fmt: (v) => v.toFixed(1),
    getValue: (pt) => pt.raw_kpis.xg,
  },
  {
    key: "assists",
    label: "Assists",
    color: "#10b981",
    getValue: (pt) => pt.raw_kpis.assists,
  },
  {
    key: "xa",
    label: "xA",
    color: "#6ee7b7",
    fmt: (v) => v.toFixed(1),
    getValue: (pt) => pt.raw_kpis.xa,
  },
  {
    key: "rating",
    label: "Rating",
    color: "#f59e0b",
    fmt: (v) => v.toFixed(2),
    getValue: (pt) => pt.raw_kpis.rating,
  },
  {
    key: "index_overall",
    label: "1vs1",
    color: "#a855f7",
    fmt: (v) => v.toFixed(0),
    getValue: (pt) => pt.raw_kpis.index_overall,
  },
];

// ── G vs xG comparison table ──────────────────────────────────────────────────
function GvsXGTable({ history }: { history: SeasonDataPoint[] }) {
  return (
    <div className="mt-3 border border-gray-100 rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead>
          <tr className="bg-gray-50 text-[9px] text-gray-400 uppercase">
            <th className="text-left px-3 py-2 font-medium">Season</th>
            <th className="text-right px-3 py-2">G / xG</th>
            <th className="text-right px-3 py-2">G − xG</th>
            <th className="text-right px-3 py-2">A / xA</th>
            <th className="text-right px-3 py-2">A − xA</th>
            <th className="text-right px-3 py-2">Rating</th>
            <th className="text-right px-3 py-2">1vs1</th>
          </tr>
        </thead>
        <tbody>
          {[...history].reverse().map((pt) => {
            const g = pt.raw_kpis.goals;
            const xg = pt.raw_kpis.xg;
            const a = pt.raw_kpis.assists;
            const xa = pt.raw_kpis.xa;
            const rating = pt.raw_kpis.rating;
            const idx = pt.raw_kpis.index_overall;
            const gd = g !== undefined && xg !== undefined ? g - xg : null;
            const ad = a !== undefined && xa !== undefined ? a - xa : null;
            const posClass = "text-green-600 font-medium";
            const negClass = "text-red-500 font-medium";
            return (
              <tr
                key={pt.season}
                className="border-t border-gray-50 hover:bg-gray-50/50 transition-colors"
              >
                <td className="px-3 py-1.5 text-gray-600 font-medium">{pt.season_label}</td>
                <td className="text-right px-3 py-1.5 tabular-nums text-gray-600">
                  {g ?? "–"} / {xg !== undefined ? xg.toFixed(1) : "–"}
                </td>
                <td
                  className={`text-right px-3 py-1.5 tabular-nums ${
                    gd !== null ? (gd >= 0 ? posClass : negClass) : "text-gray-400"
                  }`}
                >
                  {gd !== null ? (gd >= 0 ? "+" : "") + gd.toFixed(1) : "–"}
                </td>
                <td className="text-right px-3 py-1.5 tabular-nums text-gray-600">
                  {a ?? "–"} / {xa !== undefined ? xa.toFixed(1) : "–"}
                </td>
                <td
                  className={`text-right px-3 py-1.5 tabular-nums ${
                    ad !== null ? (ad >= 0 ? posClass : negClass) : "text-gray-400"
                  }`}
                >
                  {ad !== null ? (ad >= 0 ? "+" : "") + ad.toFixed(1) : "–"}
                </td>
                <td className="text-right px-3 py-1.5 tabular-nums text-gray-500">
                  {rating !== undefined ? rating.toFixed(2) : "–"}
                </td>
                <td className="text-right px-3 py-1.5 tabular-nums text-gray-500">
                  {idx !== undefined ? idx.toFixed(0) : "–"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Playing time bars ─────────────────────────────────────────────────────────
function PlayingTimeBars({ history }: { history: SeasonDataPoint[] }) {
  const MAX_MIN = 3420; // 38 × 90

  return (
    <div className="space-y-2">
      {[...history].reverse().map((pt) => {
        const minutes = pt.raw_kpis.minutes as number | undefined;
        const apps = pt.raw_kpis.apps as number | undefined;
        const starts = pt.raw_kpis.starts as number | undefined;
        const complete = pt.raw_kpis.complete_games as number | undefined;
        const minPct =
          (pt.raw_kpis.min_pct as number | undefined) ??
          (minutes ? (minutes / MAX_MIN) * 100 : 0);
        const pct = Math.min(minPct / 100, 1);
        const barColor =
          pct > 0.72 ? "#3b82f6" : pct > 0.50 ? "#6366f1" : pct > 0.28 ? "#a78bfa" : "#c4b5fd";

        return (
          <div key={pt.season} className="flex items-center gap-3">
            {/* Season label */}
            <span className="text-[9px] text-gray-400 w-12 shrink-0 text-right tabular-nums font-medium">
              {pt.season_label}
            </span>

            {/* Progress bar */}
            <div className="flex-1 relative h-6 bg-gray-100 rounded overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 rounded"
                style={{ width: `${pct * 100}%`, background: barColor, opacity: 0.8 }}
              />
              <span
                className="absolute inset-0 flex items-center px-2 text-[9px] font-semibold leading-none"
                style={{ color: pct > 0.22 ? "white" : "#6b7280" }}
              >
                {minutes ? `${minutes.toLocaleString()}'` : ""}
                {minPct ? ` · ${minPct.toFixed(0)}%` : ""}
              </span>
            </div>

            {/* Stats */}
            <div className="text-[9px] text-gray-400 tabular-nums shrink-0 w-32 flex flex-col gap-0.5">
              <span>
                {apps !== undefined ? `${apps} apps` : ""}
                {starts !== undefined ? ` · ${starts} starts` : ""}
              </span>
              {complete !== undefined && (
                <span className="text-gray-300">{complete} full 90s</span>
              )}
            </div>
          </div>
        );
      })}
      <div className="mt-1 text-[8px] text-gray-300 text-right">
        bar width = % of available minutes · max 3420 min (38 × 90)
      </div>
    </div>
  );
}

// ── Scores sparkline ──────────────────────────────────────────────────────────
function ScoresChart({
  history,
  activeLines,
  toggleLine,
}: {
  history: SeasonDataPoint[];
  activeLines: Set<string>;
  toggleLine: (key: string) => void;
}) {
  const n = history.length;
  const W = 560, H = 150;
  const ML = 32, MR = 24, MT = 14, MB = 28;
  const plotW = W - ML - MR;
  const plotH = H - MT - MB;

  function xPos(i: number) {
    return ML + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);
  }
  function yPos(v: number) {
    return MT + plotH - (v / 100) * plotH;
  }

  return (
    <div>
      {/* Line toggles */}
      <div className="flex flex-wrap items-center gap-1.5 mb-3">
        {SCORE_LINES.map((d) => (
          <button
            key={d.key}
            onClick={() => toggleLine(d.key)}
            className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border transition-colors ${
              activeLines.has(d.key)
                ? "border-transparent"
                : "border-gray-200 text-gray-400 bg-white"
            }`}
            style={
              activeLines.has(d.key)
                ? { background: d.color + "22", color: d.color, borderColor: d.color + "55" }
                : {}
            }
          >
            <span
              className="w-2 h-2 rounded-full inline-block"
              style={{ background: activeLines.has(d.key) ? d.color : "#d1d5db" }}
            />
            {d.label}
          </button>
        ))}
      </div>

      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="w-full overflow-visible">
        {/* Guide lines */}
        {[25, 50, 75].map((g) => (
          <g key={g}>
            <line
              x1={ML} x2={ML + plotW}
              y1={yPos(g)} y2={yPos(g)}
              stroke="#f3f4f6" strokeWidth={1}
            />
            <text x={ML - 4} y={yPos(g) + 3.5} fontSize={8} fill="#d1d5db" textAnchor="end">
              {g}
            </text>
          </g>
        ))}

        {/* Score lines */}
        {SCORE_LINES.filter((d) => activeLines.has(d.key)).map((def) => {
          const pts = history
            .map((pt, i) => {
              const v = getScore(pt, def.key);
              return v !== undefined ? ([xPos(i), yPos(v)] as [number, number]) : null;
            })
            .filter((p): p is [number, number] => p !== null);
          if (pts.length < 1) return null;
          const pathD = pts
            .map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`)
            .join(" ");
          return (
            <g key={def.key}>
              {pts.length >= 2 && (
                <path
                  d={pathD}
                  fill="none"
                  stroke={def.color}
                  strokeWidth={def.key === "overall" ? 2.5 : 1.75}
                  strokeLinejoin="round"
                />
              )}
              {pts.map(([cx, cy], i) => {
                const v = getScore(history[i], def.key);
                return (
                  <g key={i}>
                    <circle cx={cx} cy={cy} r={def.key === "overall" ? 4 : 3} fill={def.color} />
                    {i === pts.length - 1 && (
                      <text
                        x={cx + 6} y={cy + 3.5}
                        fontSize={8} fill={def.color} fontWeight="600"
                      >
                        {v}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* X-axis labels */}
        {history.map((pt, i) => (
          <text
            key={i}
            x={xPos(i)} y={H - 4}
            fontSize={8.5} fill="#9ca3af" textAnchor="middle"
          >
            {pt.season_label}
          </text>
        ))}
      </svg>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function SeasonTrend({ history }: Props) {
  const [activeLines, setActiveLines] = useState<Set<string>>(
    new Set(["overall", "Defence", "Possession", "Progression", "Attack"])
  );
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState<Tab>("scores");

  if (history.length < 2) return null;

  function toggleLine(key: string) {
    setActiveLines((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  const TABS: { id: Tab; label: string }[] = [
    { id: "scores", label: "Scores" },
    { id: "output", label: "Goals & Output" },
    { id: "time",   label: "Playing Time" },
  ];

  return (
    <div className="mt-5">
      {/* Collapse toggle */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors mb-2"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-90" : ""}`}
        >
          <path
            fillRule="evenodd"
            d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z"
            clipRule="evenodd"
          />
        </svg>
        Season trend
        <span className="text-gray-400 font-normal">({history.length} seasons)</span>
      </button>

      {open && (
        <div className="border border-gray-100 rounded-lg overflow-hidden bg-white">
          {/* Tab bar */}
          <div className="flex border-b border-gray-100 bg-gray-50/60">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-4 py-2.5 text-xs font-medium transition-colors ${
                  tab === t.id
                    ? "text-gray-900 bg-white border-b-2 border-gray-800 -mb-px"
                    : "text-gray-400 hover:text-gray-600"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="p-4">
            {tab === "scores" && (
              <ScoresChart
                history={history}
                activeLines={activeLines}
                toggleLine={toggleLine}
              />
            )}

            {tab === "output" && (
              <div>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                  {OUTPUT_STATS.map((def) => (
                    <StatCard key={def.key} def={def} history={history} />
                  ))}
                </div>
                <GvsXGTable history={history} />
              </div>
            )}

            {tab === "time" && <PlayingTimeBars history={history} />}
          </div>
        </div>
      )}
    </div>
  );
}

