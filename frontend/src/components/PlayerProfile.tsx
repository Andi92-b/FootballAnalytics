"use client";

import { useEffect, useState } from "react";

interface StatEntry {
  value: number;
  source: "sofascore" | "fbref" | "understat" | "footystats" | "ovo";
}

interface ProfileData {
  player: string;
  display_name: string;
  position: string;
  team: string;
  available_sources: string[];
  errors: Record<string, string>;
  merged: Record<string, StatEntry>;
  raw: Record<string, unknown>;
}

const SOURCE_COLORS: Record<string, string> = {
  sofascore:  "bg-blue-100 text-blue-800",
  fbref:      "bg-orange-100 text-orange-800",
  understat:  "bg-green-100 text-green-800",
  footystats: "bg-purple-100 text-purple-800",
  ovo:        "bg-teal-100 text-teal-800",
};

const SOURCE_LABELS: Record<string, string> = {
  sofascore:  "Sofascore",
  fbref:      "FBref",
  understat:  "Understat",
  footystats: "FootyStats",
  ovo:        "1vs1",
};

// Stat display config: key → { label, unit, decimals, category }
const STAT_CONFIG: Record<string, { label: string; unit?: string; decimals?: number; category: string }> = {
  // Attack
  goals:               { label: "Goals",                category: "Attack" },
  assists:             { label: "Assists",               category: "Attack" },
  goals_assists_sum:   { label: "G+A",                   category: "Attack" },
  npxg:                { label: "npxG",                  category: "Attack", decimals: 2 },
  xg:                  { label: "xG",                    category: "Attack", decimals: 2 },
  xa:                  { label: "xA",                    category: "Attack", decimals: 2 },
  big_chances_created: { label: "Big chances created",   category: "Attack" },
  big_chances_missed:  { label: "Big chances missed",    category: "Attack" },
  // Shooting
  total_shots:         { label: "Total shots",           category: "Shooting" },
  shots_on_target:     { label: "Shots on target",       category: "Shooting" },
  shots_understat:     { label: "Shots (Understat)",     category: "Shooting" },
  // Passing
  total_passes:        { label: "Total passes",          category: "Passing" },
  pass_accuracy_pct:   { label: "Pass accuracy",         category: "Passing", unit: "%", decimals: 1 },
  key_passes:          { label: "Key passes",            category: "Passing" },
  accurate_crosses:    { label: "Accurate crosses",      category: "Passing" },
  cross_accuracy_pct:  { label: "Cross accuracy",        category: "Passing", unit: "%", decimals: 1 },
  passes_final_third:  { label: "Passes into final ⅓",  category: "Passing" },
  passes_opp_half:     { label: "Passes in opp. half",   category: "Passing" },
  passes_own_half:     { label: "Passes in own half",    category: "Passing" },
  progressive_carries: { label: "Progressive carries",   category: "Passing" },
  passes_to_opp_box:   { label: "Passes to opp. box",    category: "Passing" },
  // Dribbling
  successful_dribbles: { label: "Successful dribbles",   category: "Dribbling" },
  dribble_success_pct: { label: "Dribble success",       category: "Dribbling", unit: "%", decimals: 1 },
  ball_losses_pct:     { label: "Ball losses % / game",  category: "Dribbling", unit: "%", decimals: 1 },
  offensive_touches:   { label: "Offensive touches",     category: "Dribbling" },
  // Defending
  tackles:             { label: "Tackles",               category: "Defending" },
  tackles_won:         { label: "Tackles won",           category: "Defending" },
  interceptions:       { label: "Interceptions",         category: "Defending" },
  fouls_committed:     { label: "Fouls committed",       category: "Defending" },
  ground_duels_won:    { label: "Ground duels won",      category: "Defending" },
  ground_duels_lost:   { label: "Ground duels lost",     category: "Defending" },
  aerial_duels_won:    { label: "Aerial duels won",      category: "Defending" },
  ball_regains:        { label: "Ball regains",          category: "Defending" },
  // General
  rating:              { label: "Avg rating",            category: "General", decimals: 2 },
  minutes:             { label: "Minutes",               category: "General" },
  yellow_cards:        { label: "Yellow cards",          category: "General" },
  red_cards:           { label: "Red cards",             category: "General" },
  index_overall:       { label: "1vs1 Index",            category: "General", decimals: 1 },
};

const CATEGORY_ORDER = ["General", "Attack", "Shooting", "Passing", "Dribbling", "Defending"];

function SourceBadge({ source }: { source: string }) {
  return (
    <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${SOURCE_COLORS[source] ?? "bg-gray-100 text-gray-700"}`}>
      {SOURCE_LABELS[source] ?? source}
    </span>
  );
}

function StatRow({ statKey, entry }: { statKey: string; entry: StatEntry }) {
  const cfg = STAT_CONFIG[statKey];
  const label = cfg?.label ?? statKey.replace(/_/g, " ");
  const decimals = cfg?.decimals ?? 0;
  const unit = cfg?.unit ?? "";
  const formatted = entry.value.toFixed(decimals) + unit;

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="py-1.5 pr-4 text-sm text-gray-700 whitespace-nowrap">{label}</td>
      <td className="py-1.5 pr-4 text-sm font-semibold text-gray-900 tabular-nums text-right">{formatted}</td>
      <td className="py-1.5"><SourceBadge source={entry.source} /></td>
    </tr>
  );
}

export function PlayerProfile() {
  const [data, setData] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/player/Luis%20Diaz/profile")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-400 text-sm">Loading profile…</p>;
  if (error)   return <p className="text-red-500 text-sm">Error: {error}</p>;
  if (!data)   return null;

  // Group stats by category
  const grouped: Record<string, Array<[string, StatEntry]>> = {};
  for (const cat of CATEGORY_ORDER) grouped[cat] = [];

  for (const [key, entry] of Object.entries(data.merged)) {
    const cat = STAT_CONFIG[key]?.category ?? "General";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push([key, entry]);
  }

  const activeSources = ["sofascore", "fbref", "understat", "footystats", "ovo"];

  return (
    <div className="w-full max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{data.display_name}</h2>
          <p className="text-gray-500 text-sm mt-0.5">{data.position} · {data.team}</p>
        </div>
        <div className="flex flex-col gap-1 items-end">
          <p className="text-xs text-gray-400 mb-1">Data sources</p>
          <div className="flex gap-1 flex-wrap justify-end">
            {activeSources.map((src) => (
              <span
                key={src}
                className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                  data.available_sources.includes(src)
                    ? SOURCE_COLORS[src]
                    : "bg-gray-100 text-gray-400 line-through"
                }`}
              >
                {SOURCE_LABELS[src]}
              </span>
            ))}
          </div>
          {Object.keys(data.errors).length > 0 && (
            <p className="text-xs text-gray-400 mt-1">
              Unavailable: {Object.keys(data.errors).filter(k => data.errors[k] !== "returned None (no data or not found)" || !data.available_sources.includes(k)).join(", ")}
            </p>
          )}
        </div>
      </div>

      {/* Stat tables by category */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {CATEGORY_ORDER.map((cat) => {
          const rows = grouped[cat];
          if (!rows || rows.length === 0) return null;
          return (
            <div key={cat}>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">{cat}</h3>
              <table className="w-full">
                <tbody>
                  {rows.map(([key, entry]) => (
                    <StatRow key={key} statKey={key} entry={entry} />
                  ))}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>
    </div>
  );
}
