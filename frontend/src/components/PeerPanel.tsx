"use client";

import { useState } from "react";
import type { MetricResult } from "@/components/PizzaChart";
import { METRIC_DESCRIPTIONS } from "@/lib/metricDescriptions";

export interface PeerEntry {
  name: string;
  team: string;
  position: string;
  apps: number;
  starts: number;
  minutes: number;
  metric_values: Record<string, number>;
  metric_percentiles?: Record<string, number>;
  tm_main_position?: string;
  tm_other_positions?: string[];
}

const TM_ABBREV: Record<string, string> = {
  "Goalkeeper": "GK",
  "Sweeper": "SW",
  "Centre-Back": "CB",
  "Left-Back": "LB",
  "Right-Back": "RB",
  "Defensive Midfield": "DM",
  "Central Midfield": "CM",
  "Attacking Midfield": "AM",
  "Left Midfield": "LM",
  "Right Midfield": "RM",
  "Left Winger": "LW",
  "Right Winger": "RW",
  "Second Striker": "SS",
  "Centre-Forward": "CF",
};

function abbrevTMPos(pos: string): string {
  return TM_ABBREV[pos] ?? pos;
}

function normalizeName(name: string): string {
  return name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function isTargetPlayer(peerName: string, playerName: string): boolean {
  return normalizeName(peerName) === normalizeName(playerName);
}

// ── MetricLeaderboard ──────────────────────────────────────────────────────────

interface LeaderboardProps {
  metric: string;
  peers: PeerEntry[];
  playerName: string;
  playerRaw: number;
}

export function MetricLeaderboard({ metric, peers, playerName, playerRaw }: LeaderboardProps) {
  const sorted = [...peers].sort(
    (a, b) => (b.metric_values[metric] ?? 0) - (a.metric_values[metric] ?? 0),
  );

  const playerIdx = sorted.findIndex(
    (p) => isTargetPlayer(p.name, playerName),
  );

  return (
    <div className="mt-4 border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
            {metric}
          </span>
          {METRIC_DESCRIPTIONS[metric] && (
            <p className="text-xs text-gray-400 mt-0.5 max-w-xs">{METRIC_DESCRIPTIONS[metric]}</p>
          )}
        </div>
        <span className="text-xs text-gray-400 shrink-0 ml-4">{sorted.length} players</span>
      </div>
      <div className="overflow-y-auto max-h-72 divide-y divide-gray-100">
        {sorted.map((peer, i) => {
          const isTarget = isTargetPlayer(peer.name, playerName);
          const val = peer.metric_values[metric] ?? 0;
          const maxVal = sorted[0]?.metric_values[metric] ?? 1;
          const pct = maxVal > 0 ? (val / maxVal) * 100 : 0;

          return (
            <div
              key={`${peer.name}-${i}`}
              className={`flex items-center gap-3 px-4 py-2 ${
                isTarget ? "bg-blue-50" : "hover:bg-gray-50"
              }`}
            >
              <span className="text-xs text-gray-400 w-5 text-right shrink-0">
                {i + 1}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-1.5">
                  <span
                    className={`text-sm truncate ${
                      isTarget ? "font-semibold text-blue-700" : "text-gray-800"
                    }`}
                  >
                    {peer.name}
                  </span>
                  <span className="text-xs text-gray-400 truncate">{peer.team}</span>
                </div>
                <div className="mt-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${isTarget ? "bg-blue-500" : "bg-gray-300"}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
              <span
                className={`text-xs tabular-nums w-12 text-right shrink-0 ${
                  isTarget ? "font-semibold text-blue-700" : "text-gray-600"
                }`}
              >
                {val.toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>
      {playerIdx >= 0 && (
        <div className="bg-gray-50 px-4 py-1.5 border-t border-gray-200 text-xs text-gray-500">
          {playerName} ranked{" "}
          <span className="font-semibold text-gray-700">#{playerIdx + 1}</span> of{" "}
          {sorted.length}
        </div>
      )}
    </div>
  );
}

// ── PeerRoster ─────────────────────────────────────────────────────────────────

interface RosterProps {
  peers: PeerEntry[];
  playerName: string;
  metrics: MetricResult[];
}

type SortKey = "name" | "team" | "minutes" | string;

const CATEGORIES = ["Defence", "Possession", "Progression", "Attack"] as const;
type Category = (typeof CATEGORIES)[number];

const CAT_COLORS: Record<Category, string> = {
  Defence:     "text-blue-700",
  Possession:  "text-emerald-700",
  Progression: "text-amber-700",
  Attack:      "text-rose-700",
};

function pctBg(v: number | undefined): string {
  if (v === undefined) return "";
  if (v >= 80) return "bg-green-100 text-green-800";
  if (v >= 60) return "bg-green-50 text-green-700";
  if (v >= 40) return "text-gray-600";
  if (v >= 20) return "bg-red-50 text-red-600";
  return "bg-red-100 text-red-700";
}

function overallScore(peer: PeerEntry): number {
  const vals = Object.values(peer.metric_percentiles ?? {});
  if (!vals.length) return 0;
  return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
}

function categoryScore(peer: PeerEntry, metrics: MetricResult[], cat: Category): number {
  const catMetrics = metrics.filter((m) => m.category === cat).map((m) => m.name);
  const vals = catMetrics.map((n) => peer.metric_percentiles?.[n] ?? 0);
  if (!vals.length) return 0;
  return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
}

export function PeerRoster({ peers, playerName, metrics }: RosterProps) {
  const [sortKey, setSortKey] = useState<SortKey>("overall");
  const [sortAsc, setSortAsc] = useState(false);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc((a) => !a);
    } else {
      setSortKey(key);
      setSortAsc(key === "name" || key === "team");
    }
  }

  const sorted = [...peers].sort((a, b) => {
    let av: number | string;
    let bv: number | string;
    if (sortKey === "name") {
      av = a.name; bv = b.name;
    } else if (sortKey === "team") {
      av = a.team; bv = b.team;
    } else if (sortKey === "position") {
      av = a.position; bv = b.position;
    } else if (sortKey === "apps") {
      av = a.apps; bv = b.apps;
    } else if (sortKey === "starts") {
      av = a.starts; bv = b.starts;
    } else if (sortKey === "minutes") {
      av = a.minutes; bv = b.minutes;
    } else if (sortKey === "overall") {
      av = overallScore(a); bv = overallScore(b);
    } else if (sortKey.startsWith("cat:")) {
      const cat = sortKey.slice(4) as Category;
      av = categoryScore(a, metrics, cat);
      bv = categoryScore(b, metrics, cat);
    } else {
      av = a.metric_percentiles?.[sortKey] ?? a.metric_values[sortKey] ?? 0;
      bv = b.metric_percentiles?.[sortKey] ?? b.metric_values[sortKey] ?? 0;
    }
    if (typeof av === "string" && typeof bv === "string") {
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
  });

  function SortIcon({ col }: { col: SortKey }) {
    if (sortKey !== col) return <span className="ml-0.5 opacity-30">↕</span>;
    return <span className="ml-0.5">{sortAsc ? "↑" : "↓"}</span>;
  }

  const thBase =
    "px-3 py-2 text-xs font-semibold uppercase tracking-wide cursor-pointer select-none hover:text-gray-800 whitespace-nowrap";
  const thL = `${thBase} text-left text-gray-500`;
  const thR = `${thBase} text-right text-gray-500`;

  function ScoreCell({ v, isTarget }: { v: number; isTarget: boolean }) {
    const colorClass = isTarget ? "font-semibold text-blue-700" : pctBg(v);
    return (
      <td className={`px-3 py-2 text-right tabular-nums text-xs rounded ${colorClass}`}>
        {v}
      </td>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full text-sm border-collapse">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {/* Identity */}
            <th className={thL} onClick={() => handleSort("name")}>Player <SortIcon col="name" /></th>
            <th className={thL} onClick={() => handleSort("team")}>Team <SortIcon col="team" /></th>
            <th className={thL} onClick={() => handleSort("position")}>Pos <SortIcon col="position" /></th>
            <th className={thL}>Main</th>
            <th className={thL}>Other</th>
            <th className={thR} onClick={() => handleSort("apps")}>Apps <SortIcon col="apps" /></th>
            <th className={thR} onClick={() => handleSort("starts")}>Starts <SortIcon col="starts" /></th>
            <th className={thR} onClick={() => handleSort("minutes")}>Min <SortIcon col="minutes" /></th>
            {/* Summary scores */}
            <th className={`${thR} border-l border-gray-300`} onClick={() => handleSort("overall")}>
              Overall <SortIcon col="overall" />
            </th>
            {CATEGORIES.map((cat) => (
              <th
                key={cat}
                className={`${thR} ${CAT_COLORS[cat]}`}
                onClick={() => handleSort(`cat:${cat}`)}
              >
                {cat.slice(0, 4)} <SortIcon col={`cat:${cat}`} />
              </th>
            ))}
            {/* Per-metric percentile scores */}
            <th className="px-1 border-l border-gray-300" />
            {metrics.map((m) => (
              <th
                key={m.name}
                className={`${thR} ${CAT_COLORS[m.category as Category] ?? "text-gray-500"}`}
                onClick={() => handleSort(m.name)}
                title={`${m.category}: ${METRIC_DESCRIPTIONS[m.name] ?? m.name}`}
              >
                {m.name} <SortIcon col={m.name} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {sorted.map((peer, i) => {
            const isTarget = isTargetPlayer(peer.name, playerName);
            const overall = overallScore(peer);
            return (
              <tr
                key={`${peer.name}-${i}`}
                className={isTarget ? "bg-blue-50 font-semibold" : "hover:bg-gray-50"}
              >
                {/* Identity */}
                <td className={`px-3 py-2 whitespace-nowrap ${isTarget ? "text-blue-700" : "text-gray-800"}`}>
                  {peer.name}
                </td>
                <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{peer.team}</td>
                <td className="px-3 py-2 text-gray-500 whitespace-nowrap font-mono text-xs">{peer.position}</td>
                <td className="px-3 py-2 text-gray-500 whitespace-nowrap font-mono text-xs">
                  {peer.tm_main_position ? abbrevTMPos(peer.tm_main_position) : ""}
                </td>
                <td className="px-3 py-2 text-gray-400 whitespace-nowrap text-xs">
                  {peer.tm_other_positions?.map(abbrevTMPos).join(", ") ?? ""}
                </td>
                <td className="px-3 py-2 text-right text-gray-600 tabular-nums">{peer.apps}</td>
                <td className="px-3 py-2 text-right text-gray-600 tabular-nums">{peer.starts}</td>
                <td className="px-3 py-2 text-right text-gray-600 tabular-nums">{peer.minutes.toLocaleString()}</td>
                {/* Summary scores */}
                <td className={`px-3 py-2 text-right tabular-nums text-xs border-l border-gray-200 font-semibold ${isTarget ? "text-blue-700" : pctBg(overall)}`}>
                  {overall}
                </td>
                {CATEGORIES.map((cat) => {
                  const score = categoryScore(peer, metrics, cat);
                  return (
                    <td
                      key={cat}
                      className={`px-3 py-2 text-right tabular-nums text-xs ${isTarget ? "text-blue-700" : pctBg(score)}`}
                    >
                      {score}
                    </td>
                  );
                })}
                {/* Per-metric percentiles */}
                <td className="px-1 border-l border-gray-200" />
                {metrics.map((m) => {
                  const pct = peer.metric_percentiles?.[m.name];
                  return (
                    <td
                      key={m.name}
                      className={`px-3 py-2 text-right tabular-nums text-xs ${isTarget ? "text-blue-700" : pctBg(pct)}`}
                      title={`${m.name}: ${(peer.metric_values[m.name] ?? 0).toFixed(2)} raw`}
                    >
                      {pct ?? "—"}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
