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
  // General
  rating:                   { label: "Avg rating",                category: "General",   decimals: 2 },
  minutes:                  { label: "Minutes played",            category: "General" },
  appearances:              { label: "Appearances",               category: "General" },
  matches_started:          { label: "Matches started",           category: "General" },
  matches_played:           { label: "Matches played (FBref)",    category: "General" },
  totw_appearances:         { label: "Team of the Week",          category: "General" },
  scorer_points_per_game:   { label: "Scorer pts / game",         category: "General",   decimals: 2 },
  scoring_frequency:        { label: "Scoring frequency (min)",   category: "General",   decimals: 0 },
  index_overall:            { label: "1vs1 Overall index",        category: "General",   decimals: 1 },
  index_offensive:          { label: "1vs1 Offensive index",      category: "General",   decimals: 1 },
  index_defensive:          { label: "1vs1 Defensive index",      category: "General",   decimals: 1 },
  // Attack
  goals:                    { label: "Goals",                     category: "Attack" },
  assists:                  { label: "Assists",                   category: "Attack" },
  goals_assists_sum:        { label: "G+A",                       category: "Attack" },
  goals_no_pen:             { label: "Goals (non-pen)",           category: "Attack" },
  npxg:                     { label: "npxG",                      category: "Attack",    decimals: 2 },
  xg:                       { label: "xG (Understat)",            category: "Attack",    decimals: 2 },
  xg_sc:                    { label: "xG (Sofascore)",            category: "Attack",    decimals: 2 },
  xa:                       { label: "xA",                        category: "Attack",    decimals: 2 },
  big_chances_created:      { label: "Big chances created",       category: "Attack" },
  big_chances_missed:       { label: "Big chances missed",        category: "Attack" },
  chances_created_ovo:      { label: "Chances created (OVO)",     category: "Attack" },
  goal_conversion_pct:      { label: "Goal conversion",          category: "Attack",    decimals: 1, unit: "%" },
  goals_per90:              { label: "Goals / 90",               category: "Attack",    decimals: 2 },
  assists_per90:            { label: "Assists / 90",             category: "Attack",    decimals: 2 },
  ga_per90:                 { label: "G+A / 90",                 category: "Attack",    decimals: 2 },
  headed_goals:             { label: "Headed goals",             category: "Attack" },
  goals_inside_box:         { label: "Goals inside box",         category: "Attack" },
  goals_outside_box:        { label: "Goals outside box",        category: "Attack" },
  goals_foot_ovo:           { label: "Goals by foot",            category: "Attack" },
  goals_headed_ovo:         { label: "Goals by head",            category: "Attack" },
  goals_long_distance:      { label: "Goals long distance",      category: "Attack" },
  hit_woodwork:             { label: "Hit woodwork",             category: "Attack" },
  offensive_interventions:  { label: "Offensive interventions",  category: "Attack",    decimals: 2 },
  penalty_won:              { label: "Penalties won",            category: "Attack" },
  // Shooting
  total_shots:              { label: "Total shots",              category: "Shooting" },
  shots_on_target:          { label: "Shots on target",          category: "Shooting" },
  shots_on_target_pct:      { label: "Shots on target",         category: "Shooting",  decimals: 1, unit: "%" },
  shots_off_target:         { label: "Shots off target",         category: "Shooting" },
  shots_inside_box:         { label: "Shots inside box",         category: "Shooting" },
  shots_outside_box:        { label: "Shots outside box",        category: "Shooting" },
  blocked_shots:            { label: "Blocked shots",            category: "Shooting" },
  shots_per90:              { label: "Shots / 90",               category: "Shooting",  decimals: 2 },
  goal_per_shot:            { label: "Goals / shot",             category: "Shooting",  decimals: 2 },
  goal_per_sot:             { label: "Goals / shot on target",   category: "Shooting",  decimals: 2 },
  shots_on_goal_ovo:        { label: "Shots on goal (OVO)",      category: "Shooting" },
  // Passing
  total_passes:             { label: "Total passes",             category: "Passing" },
  pass_accuracy_pct:        { label: "Pass accuracy",            category: "Passing",   decimals: 1, unit: "%" },
  key_passes:               { label: "Key passes",               category: "Passing" },
  passes_final_third:       { label: "Passes into final ⅓",      category: "Passing" },
  passes_opp_half:          { label: "Passes in opp. half",      category: "Passing" },
  passes_own_half:          { label: "Passes in own half",       category: "Passing" },
  passes_to_opp_box:        { label: "Passes to opp. box",       category: "Passing" },
  passes_to_final_third_ovo:{ label: "Passes to final ⅓ (OVO)",  category: "Passing" },
  passes_low_total:         { label: "Low passes (accurate)",    category: "Passing" },
  passes_low_pct:           { label: "Low pass accuracy",        category: "Passing",   decimals: 1, unit: "%" },
  accurate_crosses:         { label: "Accurate crosses",         category: "Passing" },
  cross_accuracy_pct:       { label: "Cross accuracy",           category: "Passing",   decimals: 1, unit: "%" },
  total_crosses:            { label: "Total crosses",            category: "Passing" },
  accurate_long_balls:      { label: "Accurate long balls",      category: "Passing" },
  accurate_long_balls_pct:  { label: "Long ball accuracy",       category: "Passing",   decimals: 1, unit: "%" },
  total_long_balls:         { label: "Total long balls",         category: "Passing" },
  pass_to_assist:           { label: "Pre-assists (Sofascore)",  category: "Passing" },
  crosses_fbref:            { label: "Crosses (FBref)",          category: "Passing" },
  // Dribbling
  successful_dribbles:      { label: "Successful dribbles",      category: "Dribbling" },
  dribble_success_pct:      { label: "Dribble success",          category: "Dribbling", decimals: 1, unit: "%" },
  successful_dribbles_ovo:  { label: "Successful dribbles (OVO)",category: "Dribbling" },
  dispossessed:             { label: "Dispossessed",             category: "Dribbling" },
  dribbled_past:            { label: "Dribbled past",            category: "Dribbling" },
  ball_losses_total:        { label: "Ball losses total",        category: "Dribbling" },
  ball_losses_pct:          { label: "Ball losses % / game",     category: "Dribbling", decimals: 2, unit: "%" },
  ball_losses_opp_box:      { label: "Ball losses in opp. box",  category: "Dribbling" },
  progressive_carries:      { label: "Progressive carries",      category: "Dribbling" },
  offensive_touches:        { label: "Offensive touches",        category: "Dribbling" },
  touches:                  { label: "Total touches",            category: "Dribbling" },
  possession_lost:          { label: "Possession lost",          category: "Dribbling" },
  possession_won_att_third: { label: "Possession won (att. ⅓)",  category: "Dribbling" },
  // Defending
  tackles:                  { label: "Tackles (Sofascore)",      category: "Defending" },
  tackles_ovo:              { label: "Tackles (OVO)",            category: "Defending" },
  tackles_won:              { label: "Tackles won (FBref)",      category: "Defending" },
  tackles_won_sc:           { label: "Tackles won (Sofascore)",  category: "Defending" },
  tackles_won_pct:          { label: "Tackle success",           category: "Defending", decimals: 1, unit: "%" },
  interceptions:            { label: "Interceptions (Sofascore)",category: "Defending" },
  interceptions_fbref:      { label: "Interceptions (FBref)",    category: "Defending" },
  ball_recovery:            { label: "Ball recoveries",          category: "Defending" },
  ball_regains:             { label: "Ball regains (OVO)",       category: "Defending" },
  ball_regains_opp_box:     { label: "Ball regains opp. box",    category: "Defending" },
  defensive_touches_oop:    { label: "Def. touches (out of pos)",category: "Defending" },
  ground_duels_won:         { label: "Ground duels won",         category: "Defending" },
  ground_duels_lost:        { label: "Ground duels lost",        category: "Defending" },
  ground_duels_won_pct:     { label: "Ground duel win rate",     category: "Defending", decimals: 1, unit: "%" },
  total_duels_won:          { label: "Total duels won",          category: "Defending" },
  total_duels_won_pct:      { label: "Total duel win rate",      category: "Defending", decimals: 1, unit: "%" },
  duels_lost:               { label: "Duels lost",               category: "Defending" },
  aerial_duels_won:         { label: "Aerial duels won",         category: "Defending" },
  aerial_duels_lost:        { label: "Aerial duels lost",        category: "Defending" },
  aerial_duels_won_pct:     { label: "Aerial duel win rate",     category: "Defending", decimals: 1, unit: "%" },
  clearances_head:          { label: "Clearances by head",       category: "Defending" },
  clearances_foot:          { label: "Clearances by foot",       category: "Defending" },
  fouls_committed:          { label: "Fouls committed",          category: "Defending" },
  was_fouled:               { label: "Was fouled",               category: "Defending" },
  fouls_drawn_fbref:        { label: "Fouls drawn (FBref)",      category: "Defending" },
  // Discipline
  yellow_cards:             { label: "Yellow cards",             category: "Discipline" },
  red_cards:                { label: "Red cards",                category: "Discipline" },
  offsides:                 { label: "Offsides",                 category: "Discipline" },
};

const CATEGORY_ORDER = ["General", "Attack", "Shooting", "Passing", "Dribbling", "Defending", "Discipline"];

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

  // Group stats by category — known ones by config, rest into "Other"
  const grouped: Record<string, Array<[string, StatEntry]>> = {};
  for (const cat of [...CATEGORY_ORDER, "Other"]) grouped[cat] = [];

  for (const [key, entry] of Object.entries(data.merged)) {
    const cat = STAT_CONFIG[key]?.category ?? "Other";
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...CATEGORY_ORDER, "Other"].map((cat) => {
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
