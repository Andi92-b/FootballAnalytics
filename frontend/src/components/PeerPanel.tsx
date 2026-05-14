"use client";

import { useState } from "react";
import type { MetricResult } from "@/components/PizzaChart";
import { METRIC_DESCRIPTIONS } from "@/lib/metricDescriptions";

export interface PeerEntry {
  name: string;
  team: string;
  position: string;
  minutes: number;
  metric_values: Record<string, number>;
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

export function PeerRoster({ peers, playerName, metrics }: RosterProps) {
  const [sortKey, setSortKey] = useState<SortKey>("minutes");
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
      av = a.name;
      bv = b.name;
    } else if (sortKey === "team") {
      av = a.team;
      bv = b.team;
    } else if (sortKey === "minutes") {
      av = a.minutes;
      bv = b.minutes;
    } else {
      av = a.metric_values[sortKey] ?? 0;
      bv = b.metric_values[sortKey] ?? 0;
    }
    if (typeof av === "string" && typeof bv === "string") {
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    return sortAsc
      ? (av as number) - (bv as number)
      : (bv as number) - (av as number);
  });

  function SortIcon({ col }: { col: SortKey }) {
    if (sortKey !== col) return <span className="ml-0.5 opacity-30">↕</span>;
    return <span className="ml-0.5">{sortAsc ? "↑" : "↓"}</span>;
  }

  const thClass =
    "px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 cursor-pointer select-none hover:text-gray-800 whitespace-nowrap";

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full text-sm border-collapse">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className={thClass} onClick={() => handleSort("name")}>
              Player <SortIcon col="name" />
            </th>
            <th className={thClass} onClick={() => handleSort("team")}>
              Team <SortIcon col="team" />
            </th>
            <th className={`${thClass} text-right`} onClick={() => handleSort("minutes")}>
              Min <SortIcon col="minutes" />
            </th>
            {metrics.map((m) => (
              <th
                key={m.name}
                className={`${thClass} text-right`}
                onClick={() => handleSort(m.name)}
                title={METRIC_DESCRIPTIONS[m.name]}
              >
                {m.name} <SortIcon col={m.name} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {sorted.map((peer, i) => {
            const isTarget = isTargetPlayer(peer.name, playerName);
            return (
              <tr
                key={`${peer.name}-${i}`}
                className={isTarget ? "bg-blue-50 font-semibold" : "hover:bg-gray-50"}
              >
                <td className={`px-3 py-2 whitespace-nowrap ${isTarget ? "text-blue-700" : "text-gray-800"}`}>
                  {peer.name}
                </td>
                <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{peer.team}</td>
                <td className="px-3 py-2 text-right text-gray-600 tabular-nums">
                  {peer.minutes.toLocaleString()}
                </td>
                {metrics.map((m) => (
                  <td
                    key={m.name}
                    className={`px-3 py-2 text-right tabular-nums ${
                      isTarget ? "text-blue-700" : "text-gray-600"
                    }`}
                  >
                    {(peer.metric_values[m.name] ?? 0).toFixed(2)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
