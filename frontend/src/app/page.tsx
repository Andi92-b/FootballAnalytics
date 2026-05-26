"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { PizzaChart, MetricResult } from "@/components/PizzaChart";
import { PlayerProfile } from "@/components/PlayerProfile";
import { MetricLeaderboard, PeerRoster, type PeerEntry } from "@/components/PeerPanel";
import { StyleSummary } from "@/components/StyleSummary";
import { SimilarPlayers, type SimilarPlayerData } from "@/components/SimilarPlayers";
import { PositionCard, type PlayingTimeData } from "@/components/PositionCard";
import { KeyStats, type RawStats } from "@/components/KeyStats";
import { SeasonTrend, type SeasonDataPoint } from "@/components/SeasonTrend";
import { RoleTag, type RoleData } from "@/components/RoleTag";
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
  sofascore_id?: number | null;
  sofascore_slug?: string;
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
  playing_time: PlayingTimeData | null;
  raw_stats: RawStats;
  tm_main_position: string;
  tm_other_positions: string[];
}

// Transfermarkt full position name → PositionCard pitch key
const TM_POS_TO_CODE: Record<string, string> = {
  "Goalkeeper": "GK",
  "Centre-Back": "CB",
  "Left-Back": "LB",
  "Right-Back": "RB",
  "Left Wing-Back": "LWB",
  "Right Wing-Back": "RWB",
  "Defensive Midfield": "DM",
  "Central Midfield": "CM",
  "Left Midfield": "LM",
  "Right Midfield": "RM",
  "Attacking Midfield": "AM",
  "Left Winger": "LW",
  "Right Winger": "RW",
  "Second Striker": "SS",
  "Centre-Forward": "CF",
  "Striker": "ST",
};

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
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [seasonHistory, setSeasonHistory] = useState<SeasonDataPoint[] | null>(null);
  const [roleData, setRoleData] = useState<RoleData | null>(null);

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
    setSeasonHistory(null);
    setRoleData(null);
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
      // Fetch season history in the background (non-blocking)
      fetch(`${API}/api/player/${encodeURIComponent(name)}/history`)
        .then(r => r.ok ? r.json() : null)
        .then(j => j?.history?.length >= 2 ? setSeasonHistory(j.history) : null)
        .catch(() => null);
      // Fetch tactical role
      const latestLeague = info.seasons_info[info.seasons_info.length - 1].league;
      const latestSeason = info.seasons_info[info.seasons_info.length - 1].season;
      fetch(`${API}/api/player/${encodeURIComponent(name)}/role?season=${latestSeason}&league=${encodeURIComponent(latestLeague)}`)
        .then(r => r.ok ? r.json() : null)
        .then(j => j ? setRoleData({ role: j.role, description: j.description, cluster_id: j.cluster_id, similar_players: j.similar_players }) : null)
        .catch(() => null);
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
      <p className="text-gray-500 mb-3">Position-specific pizza charts from multi-source data</p>
      <div className="mb-8 flex gap-3">
        <Link
          href="/clusters"
          className="text-xs text-indigo-500 hover:text-indigo-700 border border-indigo-200 rounded-full px-3 py-1 hover:bg-indigo-50 transition-colors"
        >
          Cluster Explorer →
        </Link>
        <Link
          href="/analysis"
          className="text-xs text-red-600 hover:text-red-800 border border-red-200 rounded-full px-3 py-1 hover:bg-red-50 transition-colors"
        >
          Bayern Analysis →
        </Link>
      </div>

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
            {(() => {
              const tmPos = data?.tm_main_position ? TM_POS_TO_CODE[data.tm_main_position] : null;
              const displayPos = tmPos ?? playerInfo.position;
              return displayPos ? <span className="ml-1 text-gray-400">· {displayPos}</span> : null;
            })()}
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

      {/* ── Main dashboard: pizza (left) + compare (right) ── */}
      <div className="w-full max-w-5xl mx-auto">

        {/* Key Numbers strip — above the two-column section */}
        {data && Object.keys(data.raw_stats ?? {}).length > 0 && (
          <div className="mb-6">
            <KeyStats stats={data.raw_stats} position={data.position} />
            {roleData && (
              <div className="mt-3">
                <RoleTag role={roleData} />
              </div>
            )}
            {seasonHistory && seasonHistory.length >= 2 && (
              <SeasonTrend history={seasonHistory} position={data.position} />
            )}
          </div>
        )}

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
              selectedMetric={selectedMetric}
              onMetricClick={(name) => {
                const cat = data?.metrics.find((m) => m.name === name)?.category ?? null;
                setSelectedCategory(cat);
                setSelectedMetric(selectedMetric === name ? null : name);
              }}
            />
          </div>

          {/* Right column: overall score + category scores + compare + inline leaderboard */}
          {data && data.metrics.length > 0 && (() => {
            const CAT_ORDER = ["Defence", "Possession", "Progression", "Attack"];
            const CAT_COLORS: Record<string, { tab: string; active: string; dot: string; bar: string }> = {
              Defence:     { tab: "hover:text-blue-600 hover:border-blue-300",    active: "text-blue-700 border-blue-500 bg-blue-50",    dot: "bg-blue-500",   bar: "bg-blue-500"   },
              Possession:  { tab: "hover:text-teal-600 hover:border-teal-300",    active: "text-teal-700 border-teal-500 bg-teal-50",    dot: "bg-teal-500",   bar: "bg-teal-500"   },
              Progression: { tab: "hover:text-purple-600 hover:border-purple-300", active: "text-purple-700 border-purple-500 bg-purple-50", dot: "bg-purple-500", bar: "bg-purple-500" },
              Attack:      { tab: "hover:text-red-600 hover:border-red-300",      active: "text-red-700 border-red-500 bg-red-50",      dot: "bg-red-500",    bar: "bg-red-500"    },
            };

            const overallScore = Math.round(
              data.metrics.reduce((s, m) => s + m.percentile, 0) / data.metrics.length
            );
            const catScores: Record<string, number> = {};
            for (const cat of CAT_ORDER) {
              const ms = data.metrics.filter((m) => m.category === cat);
              if (ms.length > 0) catScores[cat] = Math.round(ms.reduce((s, m) => s + m.percentile, 0) / ms.length);
            }

            const grouped: Record<string, typeof data.metrics> = {};
            for (const cat of CAT_ORDER) {
              const g = data.metrics.filter((m) => m.category === cat);
              if (g.length) grouped[cat] = g;
            }
            const activeCategory = selectedCategory && grouped[selectedCategory] ? selectedCategory : null;
            const visibleMetrics = activeCategory ? grouped[activeCategory] : [];

            const scoreColor = overallScore >= 75 ? "text-green-600" : overallScore >= 50 ? "text-amber-600" : "text-red-600";

            return (
              <div className="w-full lg:flex-1 lg:min-w-[300px] pt-2 flex flex-col gap-5">
                {/* Overall score */}
                <div className="flex items-center gap-4 pb-4 border-b border-gray-100">
                  <div className="flex items-end gap-1">
                    <span className={`text-5xl font-bold tabular-nums leading-none ${scoreColor}`}>{overallScore}</span>
                    <span className="text-base text-gray-400 mb-1">/99</span>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-800">Overall score</p>
                    <p className="text-xs text-gray-400">{data.metrics.length} metrics · {data.peers.length} peers</p>
                  </div>
                </div>

                {/* Category score bars */}
                <div className="space-y-2">
                  {CAT_ORDER.map((cat) => {
                    const score = catScores[cat];
                    const c = CAT_COLORS[cat];
                    return (
                      <div key={cat} className={`flex items-center gap-3 ${score == null ? "opacity-30" : ""}`}>
                        <span className="text-xs text-gray-500 w-24 shrink-0">{cat}</span>
                        <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          {score != null && <div className={`h-full rounded-full ${c.bar}`} style={{ width: `${score}%` }} />}
                        </div>
                        <span className="text-xs font-semibold tabular-nums w-6 text-right text-gray-700">
                          {score ?? "–"}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Compare by metric */}
                {data.peers.length > 0 && (
                  <div className="pt-4 border-t border-gray-100">
                    <div className="flex items-baseline gap-2 mb-3">
                      <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">Compare by metric</h2>
                      <span className="text-xs text-gray-400">{data.peers.length} peers</span>
                    </div>

                    {/* Category tabs — all 4 always shown, greyed if N/A for this position */}
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {CAT_ORDER.map((cat) => {
                        const hasMetrics = cat in catScores;
                        const isActive = selectedCategory === cat;
                        const c = CAT_COLORS[cat];
                        return (
                          <button
                            key={cat}
                            disabled={!hasMetrics}
                            onClick={() => {
                              if (!hasMetrics) return;
                              if (selectedCategory === cat) { setSelectedCategory(null); setSelectedMetric(null); }
                              else { setSelectedCategory(cat); setSelectedMetric(null); }
                            }}
                            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
                              !hasMetrics
                                ? "text-gray-300 border-gray-100 cursor-not-allowed"
                                : isActive
                                ? `${c.active} border-current`
                                : `text-gray-500 border-gray-200 ${c.tab}`
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${
                              !hasMetrics ? "bg-gray-200" : isActive ? c.dot : "bg-gray-300"
                            }`} />
                            {cat}
                          </button>
                        );
                      })}
                    </div>

                    {/* Metric pills */}
                    {activeCategory && (
                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {visibleMetrics.map((m) => (
                          <button
                            key={m.name}
                            onClick={() => setSelectedMetric(selectedMetric === m.name ? null : m.name)}
                            title={METRIC_DESCRIPTIONS[m.name]}
                            className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                              selectedMetric === m.name
                                ? "bg-blue-600 text-white border-blue-600"
                                : "bg-white text-gray-600 border-gray-200 hover:border-gray-400 hover:text-gray-900"
                            }`}
                          >
                            {m.name}
                          </button>
                        ))}
                      </div>
                    )}

                    {!activeCategory && (
                      <p className="text-xs text-gray-400">Select a category to compare metrics</p>
                    )}

                    {/* Inline leaderboard */}
                    {selectedMetric && (
                      <div className="mt-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-gray-400">showing {data.peers.length} peers</span>
                          <button
                            onClick={() => setSelectedMetric(null)}
                            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
                          >
                            ✕ close
                          </button>
                        </div>
                        <MetricLeaderboard
                          metric={selectedMetric}
                          peers={data.peers}
                          playerName={data.player}
                          playerRaw={data.metrics.find((m) => m.name === selectedMetric)?.raw ?? 0}
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })()}
        </div>

        {/* Playing Style — full width below the two-column section */}
        {data && data.metrics.length > 0 && (
          <div className="mt-10 pt-8 border-t border-gray-100">
            <StyleSummary metrics={data.metrics} position={data.position} />
          </div>
        )}

        {/* Position & Playing Time — full width below */}
        {data && data.playing_time && (() => {
          // Build a TM-derived pos string when available (more granular than FBref's MF/FW/DF)
          const tmMain = data.tm_main_position ? TM_POS_TO_CODE[data.tm_main_position] : null;
          const tmOthers = (data.tm_other_positions ?? [])
            .map((p) => TM_POS_TO_CODE[p])
            .filter(Boolean) as string[];
          const overridePos = tmMain ? [tmMain, ...tmOthers].join(",") : null;
          const playingTimeData = overridePos
            ? { ...data.playing_time, pos: overridePos }
            : data.playing_time;
          return (
            <div className="mt-10 pt-8 border-t border-gray-100">
              <PositionCard playingTime={playingTimeData} player={data.player} />
            </div>
          );
        })()}

        {/* Sofascore heatmap link */}
        {playerInfo?.sofascore_id && (
          <div className="mt-6 flex items-center gap-3">
            <span className="text-xs text-gray-400">Season heatmap:</span>
            <a
              href={`https://www.sofascore.com/player/${playerInfo.sofascore_slug ?? playerInfo.display_name.toLowerCase().replace(/\s+/g, "-")}/${playerInfo.sofascore_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline"
            >
              View on Sofascore
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3 h-3">
                <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 0 0-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 0 0 .75-.75v-4a.75.75 0 0 1 1.5 0v4A2.25 2.25 0 0 1 12.75 17h-8.5A2.25 2.25 0 0 1 2 14.75v-8.5A2.25 2.25 0 0 1 4.25 4h5a.75.75 0 0 1 0 1.5h-5Zm6.5-.25a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V6.56l-3.97 3.97a.75.75 0 0 1-1.06-1.06l3.97-3.97H10.75a.75.75 0 0 1-.75-.75Z" clipRule="evenodd" />
              </svg>
            </a>
          </div>
        )}

        {/* Similar players — full width below */}
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
