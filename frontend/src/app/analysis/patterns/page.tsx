"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = "http://localhost:8000";

interface SituationPattern {
  situation: string;
  trigger: string | null;
  count: number;
  quotes: string[];
  competition_breakdown: Record<string, number>;
}

interface PatternReport {
  defensive: SituationPattern[];
  offensive: SituationPattern[];
  total_matches_analysed: number;
  goals_conceded: number;
  goals_scored: number;
  competition_summary: Record<string, Record<string, number>>;
}

const COMPS = ["All", "Bundesliga", "Champions League", "DFB Pokal"];

const SITUATION_LABELS: Record<string, string> = {
  counterattack: "Counterattack",
  buildup_play: "Buildup Play",
  set_piece_attack: "Set Piece (Attack)",
  set_piece_defense: "Set Piece (Defense)",
  individual_error: "Individual Error",
  high_press: "High Press",
  low_block_break: "Breaking Low Block",
  transition: "Transition",
  penalty: "Penalty",
  unknown: "Unknown",
};

export default function PatternsPage() {
  const [report, setReport] = useState<PatternReport | null>(null);
  const [direction, setDirection] = useState<"defensive" | "offensive">("defensive");
  const [competition, setCompetition] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadReport() {
    setLoading(true);
    setError(null);
    try {
      const params = competition !== "All" ? `?competition=${encodeURIComponent(competition)}` : "";
      const res = await fetch(`${API}/api/analysis/patterns${params}`);
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      setReport(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadReport(); }, [competition]);

  const patterns = report ? (direction === "defensive" ? report.defensive : report.offensive) : [];
  const maxCount = Math.max(...patterns.map((p) => p.count), 1);

  return (
    <main className="min-h-screen bg-white py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <Link href="/analysis" className="text-xs text-gray-400 hover:text-gray-600">← Season Overview</Link>
            <h1 className="text-2xl font-bold text-gray-900 mt-1">Pattern Analysis</h1>
            {report && (
              <p className="text-sm text-gray-500">
                {report.total_matches_analysed} matches analysed ·{" "}
                {report.goals_scored} scored · {report.goals_conceded} conceded
              </p>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-3 mb-8">
          {/* Direction toggle */}
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {(["defensive", "offensive"] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDirection(d)}
                className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-colors capitalize ${
                  direction === d ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
                }`}
              >
                {d}
              </button>
            ))}
          </div>

          {/* Competition filter */}
          <div className="flex gap-1.5">
            {COMPS.map((c) => (
              <button
                key={c}
                onClick={() => setCompetition(c)}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${
                  competition === c
                    ? "bg-gray-900 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

        {loading ? (
          <p className="text-gray-400 text-sm">Loading…</p>
        ) : patterns.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <p className="text-sm">No patterns yet — analyse some matches first.</p>
            <Link href="/analysis" className="text-sm text-indigo-500 hover:underline mt-2 block">
              Go to Season Overview →
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {patterns.map((p, i) => (
              <PatternCard key={i} pattern={p} maxCount={maxCount} direction={direction} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function PatternCard({
  pattern: p,
  maxCount,
  direction,
}: {
  pattern: SituationPattern;
  maxCount: number;
  direction: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const barWidth = Math.round((p.count / maxCount) * 100);
  const barColor = direction === "defensive" ? "bg-red-400" : "bg-green-500";

  return (
    <div className="border border-gray-100 rounded-xl p-4 hover:border-gray-200 transition-colors">
      <div className="flex items-center gap-4 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex-1">
          <div className="flex items-baseline gap-2 mb-1.5">
            <span className="font-semibold text-gray-900 text-sm">
              {SITUATION_LABELS[p.situation] ?? p.situation}
            </span>
            {p.trigger && (
              <span className="text-xs text-gray-400">
                via {p.trigger.replace(/_/g, " ")}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${barColor}`} style={{ width: `${barWidth}%` }} />
            </div>
            <span className="text-xs font-bold text-gray-700 w-8 text-right">{p.count}×</span>
          </div>
        </div>
        <div className="flex gap-1 shrink-0">
          {Object.entries(p.competition_breakdown).map(([comp, count]) => (
            <span key={comp} className="text-xs text-gray-400">
              {comp.replace("Champions League", "CL").replace("Bundesliga", "BL").replace("DFB Pokal", "DFB")}: {count}
            </span>
          ))}
        </div>
        <span className="text-gray-300 text-xs">{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && p.quotes.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-50 space-y-2">
          {p.quotes.map((q, i) => (
            <blockquote key={i} className="text-xs text-gray-600 italic pl-3 border-l-2 border-gray-200">
              {q}
            </blockquote>
          ))}
        </div>
      )}
    </div>
  );
}
