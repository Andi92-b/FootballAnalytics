"use client";

import { useState } from "react";
import { PizzaChart, MetricResult } from "@/components/PizzaChart";

interface PlayerData {
  player: string;
  position: string;
  season: string;
  league: string;
  metrics: MetricResult[];
  svg: string;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [season, setSeason] = useState("2024");
  const [league, setLeague] = useState("ENG-Premier League");
  const [data, setData] = useState<PlayerData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const url = `http://localhost:8000/api/player/${encodeURIComponent(query.trim())}?season=${season}&league=${encodeURIComponent(league)}`;
      const res = await fetch(url);
      if (res.status === 404) throw new Error(`Player "${query}" not found`);
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

      <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2 w-full max-w-lg mb-10">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Player name (e.g. Virgil van Dijk)"
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
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
        isLoading={isLoading}
        error={error}
      />
    </main>
  );
}
