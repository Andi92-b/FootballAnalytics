"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API = "http://localhost:8000";

interface MatchInfo {
  id: string;
  date: string;
  competition: string;
  home_team: string;
  away_team: string;
  home_goals: number | null;
  away_goals: number | null;
  analysed: number;
}

interface MatchEvent {
  id: number;
  match_id: string;
  minute: number | null;
  type: string;
  direction: string;
  situation: string;
  trigger: string | null;
  defensive_cover: string | null;
  players_involved: string;
  outcome: string;
  description: string;
  confidence: string;
}

interface MatchDetail {
  match: MatchInfo;
  events: MatchEvent[];
  shots: unknown[];
  sources: { id: number; source: string; fetched_at: string }[];
}

const EVENT_TYPE_ICONS: Record<string, string> = {
  goal: "⚽",
  big_chance: "🔥",
  chance_created: "➕",
  chance_conceded: "⚠️",
  pressing_success: "💪",
  pressing_failure: "😬",
  tactical_change: "🔄",
  substitution: "🔁",
};

const DIRECTION_COLORS: Record<string, string> = {
  offensive: "bg-green-50 border-green-200",
  defensive: "bg-red-50 border-red-200",
};

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "text-green-600",
  medium: "text-amber-600",
  low: "text-gray-400",
};

export default function MatchDetailPage() {
  const params = useParams();
  const matchId = params.id as string;

  const [detail, setDetail] = useState<MatchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fetching, setFetching] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [dirFilter, setDirFilter] = useState<"all" | "offensive" | "defensive">("all");

  async function loadDetail() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/analysis/match/${encodeURIComponent(matchId)}`);
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      setDetail(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function fetchText() {
    setFetching(true);
    try {
      await fetch(`${API}/api/analysis/fetch/${encodeURIComponent(matchId)}`, { method: "POST" });
      await loadDetail();
    } finally {
      setFetching(false);
    }
  }

  async function extractEvents() {
    setExtracting(true);
    try {
      await fetch(`${API}/api/analysis/extract/${encodeURIComponent(matchId)}`, { method: "POST" });
      await loadDetail();
    } finally {
      setExtracting(false);
    }
  }

  useEffect(() => { loadDetail(); }, [matchId]);

  const m = detail?.match;
  const events = (detail?.events ?? []).filter(
    (e) => dirFilter === "all" || e.direction === dirFilter
  );

  return (
    <main className="min-h-screen bg-white py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <Link href="/analysis" className="text-xs text-gray-400 hover:text-gray-600">
          ← Season Overview
        </Link>

        {error && <p className="text-red-500 text-sm mt-4">{error}</p>}

        {loading ? (
          <p className="text-gray-400 text-sm mt-6">Loading…</p>
        ) : m ? (
          <>
            {/* Match header */}
            <div className="mt-4 mb-6">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs text-gray-400">{m.date} · {m.competition}</span>
                  <h1 className="text-2xl font-bold text-gray-900 mt-1">
                    {m.home_team} {m.home_goals != null ? `${m.home_goals} : ${m.away_goals}` : "vs"} {m.away_team}
                  </h1>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full font-semibold ${
                  m.analysed ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                }`}>
                  {m.analysed ? "Analysed" : "Not analysed"}
                </span>
              </div>

              {/* Sources */}
              {detail!.sources.length > 0 && (
                <div className="flex gap-2 mt-2 flex-wrap">
                  {detail!.sources.map((s) => (
                    <span key={s.id} className="text-xs bg-gray-100 text-gray-500 rounded px-2 py-0.5">
                      {s.source}
                    </span>
                  ))}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 mt-4">
                <button
                  onClick={fetchText}
                  disabled={fetching}
                  className="text-sm border border-gray-200 text-gray-600 rounded-lg px-4 py-2 hover:bg-gray-50 disabled:opacity-50"
                >
                  {fetching ? "Fetching…" : "Fetch text sources"}
                </button>
                {detail!.sources.length > 0 && !m.analysed && (
                  <button
                    onClick={extractEvents}
                    disabled={extracting}
                    className="text-sm bg-gray-900 text-white rounded-lg px-4 py-2 hover:bg-gray-700 disabled:opacity-50"
                  >
                    {extracting ? "Extracting…" : "Extract events (LLM)"}
                  </button>
                )}
              </div>
            </div>

            {/* Events */}
            {events.length > 0 ? (
              <>
                <div className="flex gap-2 mb-4">
                  {(["all", "offensive", "defensive"] as const).map((d) => (
                    <button
                      key={d}
                      onClick={() => setDirFilter(d)}
                      className={`text-xs px-3 py-1.5 rounded-full font-semibold transition-colors capitalize ${
                        dirFilter === d ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      {d} {d !== "all" && `(${detail!.events.filter((e) => e.direction === d).length})`}
                    </button>
                  ))}
                </div>
                <div className="space-y-3">
                  {events.map((ev) => (
                    <EventCard key={ev.id} event={ev} />
                  ))}
                </div>
              </>
            ) : m.analysed ? (
              <p className="text-sm text-gray-400">No events found for this match.</p>
            ) : (
              <div className="text-center py-16 text-gray-400">
                <p className="text-sm">No events yet.</p>
                {detail!.sources.length === 0 && (
                  <p className="text-xs mt-1">Fetch text sources first, then run LLM extraction.</p>
                )}
              </div>
            )}
          </>
        ) : null}
      </div>
    </main>
  );
}

function EventCard({ event: ev }: { event: MatchEvent }) {
  let players: string[] = [];
  try { players = JSON.parse(ev.players_involved || "[]"); } catch { /* ignore */ }

  return (
    <div className={`border rounded-xl p-4 ${DIRECTION_COLORS[ev.direction] ?? "border-gray-100"}`}>
      <div className="flex items-start gap-3">
        <span className="text-lg shrink-0">{EVENT_TYPE_ICONS[ev.type] ?? "•"}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            {ev.minute != null && (
              <span className="text-xs font-bold text-gray-500">{ev.minute}'</span>
            )}
            <span className="text-sm font-semibold text-gray-900 capitalize">
              {ev.type.replace(/_/g, " ")}
            </span>
            <span className="text-xs text-gray-400 capitalize">
              {ev.situation?.replace(/_/g, " ")}
            </span>
            {ev.trigger && (
              <span className="text-xs text-gray-300">via {ev.trigger.replace(/_/g, " ")}</span>
            )}
            <span className={`text-xs ${CONFIDENCE_COLORS[ev.confidence] ?? "text-gray-400"} ml-auto`}>
              {ev.confidence}
            </span>
          </div>
          {ev.description && (
            <p className="text-xs text-gray-600 italic mt-1">{ev.description}</p>
          )}
          {players.length > 0 && (
            <div className="flex gap-1 flex-wrap mt-1.5">
              {players.map((p) => (
                <span key={p} className="text-xs bg-white/60 border border-gray-200 rounded px-1.5 py-0.5 text-gray-600">
                  {p}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
