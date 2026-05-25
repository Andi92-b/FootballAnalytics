"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = "http://localhost:8000";

interface Match {
  id: string;
  date: string;
  competition: string;
  home_team: string;
  away_team: string;
  home_goals: number | null;
  away_goals: number | null;
  analysed: number;
}

const COMPS = ["All", "Bundesliga", "Champions League", "DFB Pokal"];

const COMP_COLORS: Record<string, string> = {
  Bundesliga: "bg-red-100 text-red-700",
  "Champions League": "bg-blue-100 text-blue-700",
  "DFB Pokal": "bg-gray-100 text-gray-600",
};

export default function AnalysisPage() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadMatches() {
    setLoading(true);
    setError(null);
    try {
      const url = filter === "All"
        ? `${API}/api/analysis/matches`
        : `${API}/api/analysis/matches?competition=${encodeURIComponent(filter)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      setMatches(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load matches");
    } finally {
      setLoading(false);
    }
  }

  async function refreshCatalogue() {
    setRefreshing(true);
    try {
      await fetch(`${API}/api/analysis/matches/refresh`, { method: "POST" });
      await loadMatches();
    } catch {
      // non-critical
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => { loadMatches(); }, [filter]);

  const analysed = matches.filter((m) => m.analysed).length;

  const summary = { W: 0, D: 0, L: 0, gf: 0, ga: 0 };
  for (const m of matches) {
    if (m.home_goals == null) continue;
    const isBayernHome = m.home_team.includes("Bayern") || m.home_team.includes("FC Bayern");
    const gf = isBayernHome ? m.home_goals : (m.away_goals ?? 0);
    const ga = isBayernHome ? (m.away_goals ?? 0) : m.home_goals;
    summary.gf += gf;
    summary.ga += ga;
    if (gf > ga) summary.W++;
    else if (gf === ga) summary.D++;
    else summary.L++;
  }

  return (
    <main className="min-h-screen bg-white py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-2">
          <div>
            <Link href="/" className="text-xs text-gray-400 hover:text-gray-600">← Home</Link>
            <h1 className="text-2xl font-bold text-gray-900 mt-1">Bayern München 2025-26</h1>
            <p className="text-sm text-gray-500">Playing style analysis across all competitions</p>
          </div>
          <div className="flex gap-2">
            <Link
              href="/analysis/patterns"
              className="text-sm bg-gray-900 text-white rounded-lg px-4 py-2 hover:bg-gray-700"
            >
              Pattern Analysis →
            </Link>
            <button
              onClick={refreshCatalogue}
              disabled={refreshing}
              className="text-sm border border-gray-200 text-gray-600 rounded-lg px-4 py-2 hover:bg-gray-50 disabled:opacity-50"
            >
              {refreshing ? "Refreshing…" : "Sync schedule"}
            </button>
          </div>
        </div>

        {/* Summary stats */}
        {matches.length > 0 && (
          <div className="flex gap-6 mt-6 mb-8 p-4 bg-gray-50 rounded-xl">
            <Stat label="Matches" value={String(matches.length)} />
            <Stat label="Analysed" value={`${analysed}/${matches.length}`} />
            <Stat label="Record" value={`${summary.W}W ${summary.D}D ${summary.L}L`} />
            <Stat label="Goals" value={`${summary.gf} : ${summary.ga}`} />
          </div>
        )}

        {/* Competition filter */}
        <div className="flex gap-2 mb-6">
          {COMPS.map((c) => (
            <button
              key={c}
              onClick={() => setFilter(c)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors ${
                filter === c
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {c}
            </button>
          ))}
        </div>

        {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

        {loading ? (
          <p className="text-gray-400 text-sm">Loading…</p>
        ) : matches.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <p className="text-sm mb-3">No matches yet.</p>
            <button onClick={refreshCatalogue} className="text-sm text-indigo-500 hover:underline">
              Sync schedule from Transfermarkt
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {matches.map((m) => (
              <MatchRow key={m.id} match={m} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-lg font-bold text-gray-900">{value}</p>
    </div>
  );
}

function MatchRow({ match: m }: { match: Match }) {
  const scored = m.home_goals != null;
  const isBayernHome = m.home_team.includes("Bayern") || m.home_team.includes("FC Bayern");
  const gf = isBayernHome ? m.home_goals : m.away_goals;
  const ga = isBayernHome ? m.away_goals : m.home_goals;
  const result = scored
    ? gf != null && ga != null
      ? gf > ga ? "W" : gf === ga ? "D" : "L"
      : ""
    : "";

  const resultColors: Record<string, string> = {
    W: "bg-green-100 text-green-700",
    D: "bg-yellow-100 text-yellow-700",
    L: "bg-red-100 text-red-700",
  };

  return (
    <Link href={`/analysis/match/${m.id}`} className="flex items-center gap-4 py-3 hover:bg-gray-50 px-2 rounded-lg transition-colors group">
      <span className="text-xs text-gray-400 w-24 shrink-0">{m.date}</span>
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${COMP_COLORS[m.competition] ?? "bg-gray-100 text-gray-600"}`}>
        {m.competition}
      </span>
      <span className="flex-1 text-sm text-gray-900 font-medium truncate">
        {m.home_team} vs {m.away_team}
      </span>
      {scored && (
        <span className="text-sm font-bold text-gray-900 w-12 text-center">
          {m.home_goals} : {m.away_goals}
        </span>
      )}
      {result && (
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${resultColors[result]}`}>
          {result}
        </span>
      )}
      <span className={`text-xs w-20 text-right shrink-0 ${m.analysed ? "text-green-600" : "text-gray-300"}`}>
        {m.analysed ? "Analysed" : "Pending"}
      </span>
    </Link>
  );
}
