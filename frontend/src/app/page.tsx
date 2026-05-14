"use client";

import { useState, useEffect, useRef } from "react";
import { PizzaChart, MetricResult } from "@/components/PizzaChart";
import { PlayerProfile } from "@/components/PlayerProfile";
import { MetricLeaderboard, PeerRoster, type PeerEntry } from "@/components/PeerPanel";
import { StyleSummary } from "@/components/StyleSummary";
import { SimilarPlayers, type SimilarPlayerData } from "@/components/SimilarPlayers";
import { METRIC_DESCRIPTIONS } from "@/lib/metricDescriptions";

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
  peers: PeerEntry[];
  similar_players: SimilarPlayerData[];
}

interface SearchSuggestion {
  name: string;
  team: string;
  league: string;
  position: string;
  season: number;
  minutes: number;
}

function seasonLabel(year: number): string {
  return `${year}/${String(year + 1).slice(2)}`;
}

function leagueShort(league: string): string {
  const map: Record<string, string> = {
    "ENG-Premier League": "PL",
    "GER-Bundesliga": "BL",
    "ESP-La Liga": "LL",
    "ITA-Serie A": "SA",
    "FRA-Ligue 1": "L1",
  };
  return map[league] ?? league.replace(/^[A-Z]+-/, "");
}

export default function Home() {
  const [nameInput, setNameInput] = useState("");
  const [playerInfo, setPlayerInfo] = useState<PlayerSeasonsInfo | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [selectedLeague, setSelectedLeague] = useState<string | null>(null);
  const [data, setData] = useState<PlayerData | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingChart, setIsLoadingChart] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null);

  // Autocomplete
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIdx, setHighlightedIdx] = useState(-1);
  const searchContainerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch suggestions on input change (debounced 250ms)
  useEffect(() => {
    const q = nameInput.trim();
    if (q.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/api/players/search?q=${encodeURIComponent(q)}&limit=8`);
        if (res.ok) {
          const data: SearchSuggestion[] = await res.json();
          setSuggestions(data);
          setShowSuggestions(data.length > 0);
          setHighlightedIdx(-1);
        }
      } catch {
        // search failure is non-critical
      }
    }, 250);
  }, [nameInput]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function selectSuggestion(s: SearchSuggestion) {
    setNameInput(s.name);
    setShowSuggestions(false);
    setSuggestions([]);
    setHighlightedIdx(-1);
    triggerSearch(s.name);
  }

  async function triggerSearch(name: string) {
    if (!name.trim()) return;
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
      const latest = info.seasons_info[info.seasons_info.length - 1];
      await loadSeason(info, latest.season, latest.league);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsSearching(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setShowSuggestions(false);
    await triggerSearch(nameInput.trim());
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!showSuggestions || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIdx((i) => Math.max(i - 1, -1));
    } else if (e.key === "Enter" && highlightedIdx >= 0) {
      e.preventDefault();
      selectSuggestion(suggestions[highlightedIdx]);
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  }

  async function loadSeason(info: PlayerSeasonsInfo, season: number, league: string) {
    setSelectedSeason(season);
    setSelectedLeague(league);
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
      setSelectedMetric(null);
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

      {/* ── Search form with autocomplete ── */}
      <div ref={searchContainerRef} className="relative w-full max-w-lg mb-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
            placeholder="Search player, e.g. Anthony Gordon"
            autoComplete="off"
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

        {/* Dropdown */}
        {showSuggestions && (
          <ul className="absolute z-10 w-full bg-white border border-gray-200 rounded-lg shadow-lg mt-1 overflow-hidden">
            {suggestions.map((s, i) => (
              <li
                key={`${s.name}-${s.league}`}
                onMouseDown={() => selectSuggestion(s)}
                className={`px-4 py-2.5 cursor-pointer flex items-center justify-between gap-3 ${
                  i === highlightedIdx ? "bg-blue-50" : "hover:bg-gray-50"
                }`}
              >
                <span className="font-medium text-sm text-gray-900 truncate">{s.name}</span>
                <span className="text-xs text-gray-400 shrink-0">
                  {s.team} · {leagueShort(s.league)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

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

      {/* ── Main dashboard: pizza (left) + style summary (right) ── */}
      <div className="w-full max-w-5xl mx-auto">
        <div className={`flex flex-col ${data?.metrics.length ? "lg:flex-row" : ""} gap-8 items-start`}>
          {/* Pizza chart */}
          <div className="w-full lg:w-auto lg:shrink-0">
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
          </div>

          {/* Style summary — only when data loaded */}
          {data && data.metrics.length > 0 && (
            <div className="w-full lg:flex-1 lg:min-w-[280px] lg:max-w-sm pt-2">
              <StyleSummary metrics={data.metrics} position={data.position} />
            </div>
          )}
        </div>

        {/* Similar players — full width below the two columns */}
        {data && data.similar_players.length > 0 && (
          <div className="mt-10 pt-8 border-t border-gray-100">
            <SimilarPlayers
              players={data.similar_players}
              currentPlayer={data.player}
              onSelect={(name) => triggerSearch(name)}
            />
          </div>
        )}
      </div>

      {/* ── Metric leaderboard (peer comparison) ── */}
      {data && data.peers.length > 0 && (
        <div className="w-full max-w-5xl mx-auto mt-8">
          <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
            Compare by metric — {data.peers.length} peers
          </p>
          <div className="flex flex-wrap gap-2">
            {data.metrics.map((m) => (
              <button
                key={m.name}
                onClick={() => setSelectedMetric(selectedMetric === m.name ? null : m.name)}
                title={METRIC_DESCRIPTIONS[m.name]}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  selectedMetric === m.name
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {m.name}
              </button>
            ))}
          </div>
          {selectedMetric && (
            <MetricLeaderboard
              metric={selectedMetric}
              peers={data.peers}
              playerName={data.player}
              playerRaw={data.metrics.find((m) => m.name === selectedMetric)?.raw ?? 0}
            />
          )}
        </div>
      )}

      {/* ── Stats Dashboard ── */}
      {playerInfo && selectedSeason && selectedLeague && (
        <>
          <hr className="w-full max-w-5xl border-gray-200 my-12" />
          <section className="w-full max-w-5xl">
            <h2 className="text-xl font-semibold text-gray-800 mb-1">
              Player Stats Dashboard
            </h2>
            <p className="text-sm text-gray-400 mb-6">
              Raw scraped data for{" "}
              <span className="font-medium text-gray-600">{playerInfo.display_name}</span>
              {" · "}
              <span className="font-medium text-gray-600">{seasonLabel(selectedSeason)}</span>
              {" · "}
              <span className="text-gray-500">{selectedLeague.replace(/^[A-Z]+-/, "")}</span>
            </p>
            <PlayerProfile
              playerName={playerInfo.player}
              season={selectedSeason}
              league={selectedLeague}
            />
            {data && data.peers.length > 0 && (
              <>
                <hr className="border-gray-100 my-8" />
                <h3 className="text-base font-semibold text-gray-800 mb-1">
                  Peer Group Roster
                </h3>
                <p className="text-xs text-gray-400 mb-4">
                  {data.peers.length} players · {data.position} · {data.league.replace(/^[A-Z]+-/, "")} · {data.season}
                </p>
                <PeerRoster
                  peers={data.peers}
                  playerName={data.player}
                  metrics={data.metrics}
                />
              </>
            )}
          </section>
        </>
      )}
    </main>
  );
}
