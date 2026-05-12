"use client";

import { useState } from "react";
import { PizzaChart, MetricResult } from "@/components/PizzaChart";
import { PlayerProfile } from "@/components/PlayerProfile";

const API = "http://localhost:8000";

interface PlayerSeasonsInfo {
  player: string;
  display_name: string;
  league: string;
  position: string;
  team: string;
  seasons: number[];
  seasons_info: { season: number; league: string }[];
}

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

function seasonLabel(year: number): string {
  return `${year}/${String(year + 1).slice(2)}`;
}

export default function Home() {
  const [nameInput, setNameInput] = useState("");
  const [playerInfo, setPlayerInfo] = useState<PlayerSeasonsInfo | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [data, setData] = useState<PlayerData | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingChart, setIsLoadingChart] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const name = nameInput.trim();
    if (!name) return;
    setIsSearching(true);
    setError(null);
    setPlayerInfo(null);
    setSelectedSeason(null);
    setData(null);
    try {
      const res = await fetch(`${API}/api/player/${encodeURIComponent(name)}/seasons`);
      if (res.status === 404) {
        const j = await res.json();
        throw new Error(j.detail);
      }
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const info: PlayerSeasonsInfo = await res.json();
      setPlayerInfo(info);
      // Auto-load the most recent season
      const latest = info.seasons_info[info.seasons_info.length - 1];
      await loadSeason(info, latest.season, latest.league);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsSearching(false);
    }
  }

  async function loadSeason(info: PlayerSeasonsInfo, season: number, league: string) {
    setSelectedSeason(season);
    setIsLoadingChart(true);
    setError(null);
    try {
      const url = `${API}/api/player/${encodeURIComponent(info.player)}?season=${season}&league=${encodeURIComponent(league)}`;
      const res = await fetch(url);
      if (res.status === 404) throw new Error(`No data for ${info.display_name} in ${seasonLabel(season)}`);
      if (res.status === 422) {
        const j = await res.json();
        throw new Error(j.detail);
      }
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setData(null);
    } finally {
      setIsLoadingChart(false);
    }
  }

  const isLoading = isSearching || isLoadingChart;

  return (
    <main className="min-h-screen bg-white flex flex-col items-center py-16 px-4">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Football Analytics</h1>
      <p className="text-gray-500 mb-8">Position-specific pizza charts from multi-source data</p>

      {/* ── Search form ── */}
      <form onSubmit={handleSearch} className="flex gap-2 w-full max-w-lg mb-4">
        <input
          type="text"
          value={nameInput}
          onChange={(e) => setNameInput(e.target.value)}
          placeholder="Player name, e.g. Luis Diaz"
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="bg-blue-600 text-white rounded-lg px-5 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {isSearching ? "Searching…" : "Search"}
        </button>
      </form>

      {/* ── Season dropdown (appears after search) ── */}
      {playerInfo && (
        <div className="flex items-center gap-3 mb-8">
          <span className="text-sm text-gray-600">
            <span className="font-medium text-gray-900">{playerInfo.display_name}</span>
            {playerInfo.position && (
              <span className="ml-1 text-gray-400">· {playerInfo.position}</span>
            )}
            {playerInfo.team && (
              <span className="ml-1 text-gray-400">· {playerInfo.team}</span>
            )}
          </span>
          <span className="text-gray-300">|</span>
          <div className="flex gap-1.5">
            {[...playerInfo.seasons_info].reverse().map(({ season, league }) => (
              <button
                key={season}
                onClick={() => loadSeason(playerInfo, season, league)}
                disabled={isLoadingChart}
                title={league}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  selectedSeason === season
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                } disabled:opacity-50`}
              >
                {seasonLabel(season)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Pizza chart ── */}
      <PizzaChart
        svg={data?.svg ?? ""}
        player={data?.player ?? ""}
        position={data?.position ?? ""}
        season={data?.season ?? ""}
        league={data?.league ?? ""}
        metrics={data?.metrics ?? []}
        missingMetrics={data?.missing_metrics ?? []}
        dataSources={data?.data_sources ?? []}
        isLoading={isLoadingChart}
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
