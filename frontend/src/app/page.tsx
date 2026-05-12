"use client";

import { useState } from "react";
import { PizzaChart, MetricResult } from "@/components/PizzaChart";
import { PlayerProfile } from "@/components/PlayerProfile";

interface PlayerData {
  player: string;
  position: string;
  season: string;
  league: string;
  metrics: MetricResult[];
  missing_metrics: string[];
  data_sources: string[];
  svg: string;
}

export default function Home() {
  const [fbrefUrl, setFbrefUrl] = useState("");
  const [season, setSeason] = useState("2024");
  const [league, setLeague] = useState("ENG-Premier League");

  const LEAGUES = [
    { group: "Domestic", options: [
      { value: "ENG-Premier League", label: "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League" },
      { value: "ESP-La Liga",        label: "🇪🇸 La Liga" },
      { value: "GER-Bundesliga",     label: "🇩🇪 Bundesliga" },
      { value: "ITA-Serie A",        label: "🇮🇹 Serie A" },
      { value: "FRA-Ligue 1",        label: "🇫🇷 Ligue 1" },
    ]},
    { group: "International", options: [
      { value: "INT-World Cup",              label: "🌍 World Cup" },
      { value: "INT-European Championship",  label: "🇪🇺 European Championship" },
      { value: "INT-Women's World Cup",      label: "🌍 Women's World Cup" },
    ]},
  ];
  const [data, setData] = useState<PlayerData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function parseNameFromUrl(raw: string): string {
    // Handles both profile URLs and season-specific URLs:
    // https://fbref.com/en/players/\<id\>/Virgil-van-Dijk
    // https://fbref.com/en/players/\<id\>/2024-2025/Virgil-van-Dijk
    const clean = raw.trim().replace(/\/$/, "");
    const parts = clean.split("/").filter(Boolean);
    const last = parts[parts.length - 1] ?? "";
    // If last segment looks like a season (e.g. "2024-2025"), use the one before
    if (/^\d{4}-\d{4}$/.test(last)) {
      return (parts[parts.length - 2] ?? "").replace(/-/g, " ");
    }
    return last.replace(/-/g, " ");
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!fbrefUrl.trim()) return;
    const playerName = parseNameFromUrl(fbrefUrl);
    if (!playerName) {
      setError("Could not parse player name from URL");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const url = `http://localhost:8000/api/player/${encodeURIComponent(playerName)}?season=${season}&league=${encodeURIComponent(league)}`;
      const res = await fetch(url);
      if (res.status === 404) throw new Error(`Player "${playerName}" not found in ${league} ${season}`);
      if (res.status === 422) {
        const j = await res.json();
        throw new Error(j.detail);
      }
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-white flex flex-col items-center py-16 px-4">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Football Analytics</h1>
      <p className="text-gray-500 mb-8">Position-specific pizza charts from FBref data</p>

      <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2 w-full max-w-2xl mb-10">
        <input
          type="url"
          value={fbrefUrl}
          onChange={(e) => setFbrefUrl(e.target.value)}
          placeholder="https://fbref.com/en/players/e46012d0/Virgil-van-Dijk"
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <select
          value={league}
          onChange={(e) => setLeague(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          {LEAGUES.map((g) => (
            <optgroup key={g.group} label={g.group}>
              {g.options.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </optgroup>
          ))}
        </select>
        <input
          type="number"
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          placeholder="Season"
          className="w-24 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="bg-blue-600 text-white rounded-lg px-5 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? "Loading…" : "Search"}
        </button>
      </form>

      <PizzaChart
        svg={data?.svg ?? ""}
        player={data?.player ?? ""}
        position={data?.position ?? ""}
        season={data?.season ?? ""}
        league={data?.league ?? ""}
        metrics={data?.metrics ?? []}
        missingMetrics={data?.missing_metrics ?? []}
        dataSources={data?.data_sources ?? []}
        isLoading={isLoading}
        error={error}
      />

      {/* ── Stats Dashboard ── */}
      <hr className="w-full max-w-3xl border-gray-200 my-12" />
      <section className="w-full max-w-3xl">
        <h2 className="text-xl font-semibold text-gray-800 mb-6">
          Player Stats Dashboard
          <span className="ml-2 text-sm font-normal text-gray-400">— Luis Díaz · Bayern München</span>
        </h2>
        <PlayerProfile />
      </section>
    </main>
  );
}
