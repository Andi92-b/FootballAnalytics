"use client";

export interface SimilarPlayerData {
  name: string;
  team: string;
  position: string;
  minutes: number;
  similarity: number;
  metric_values: Record<string, number>;
}

const POSITION_FULL: Record<string, string> = {
  CB: "Centre-back",
  FB: "Full-back",
  DM: "Def. Mid",
  CM: "Central Mid",
  AM: "Att. Mid",
  W:  "Winger",
  CF: "Striker",
  GK: "Goalkeeper",
};

function similarityLabel(sim: number): string {
  if (sim >= 0.99) return "Near identical";
  if (sim >= 0.97) return "Very similar";
  if (sim >= 0.94) return "Similar";
  if (sim >= 0.90) return "Comparable";
  return "Loosely similar";
}

function similarityColor(sim: number): string {
  if (sim >= 0.97) return "text-emerald-600";
  if (sim >= 0.94) return "text-blue-600";
  if (sim >= 0.90) return "text-gray-500";
  return "text-gray-400";
}

interface SimilarPlayersProps {
  players: SimilarPlayerData[];
  onSelect: (name: string) => void;
  currentPlayer: string;
}

export function SimilarPlayers({ players, onSelect, currentPlayer }: SimilarPlayersProps) {
  if (players.length === 0) return null;

  return (
    <div className="w-full">
      <div className="flex items-baseline gap-2 mb-4">
        <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">Similar Players</h2>
        <span className="text-xs text-gray-400">by playing style · click to compare</span>
      </div>

      <div className="space-y-1.5">
        {players.map((p, i) => (
          <button
            key={p.name}
            onClick={() => onSelect(p.name)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 transition-colors text-left group"
          >
            {/* Rank */}
            <span className="text-xs font-bold text-gray-300 w-4 shrink-0 group-hover:text-gray-400">
              {i + 1}
            </span>

            {/* Name + team */}
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium text-gray-900 truncate block">{p.name}</span>
              <span className="text-xs text-gray-400 truncate block">
                {p.team} · {POSITION_FULL[p.position] ?? p.position}
              </span>
            </div>

            {/* Similarity */}
            <div className="text-right shrink-0">
              <span className={`text-xs font-semibold ${similarityColor(p.similarity)}`}>
                {similarityLabel(p.similarity)}
              </span>
              <span className="text-xs text-gray-300 block">
                {(p.similarity * 100).toFixed(1)}%
              </span>
            </div>
          </button>
        ))}
      </div>

      <p className="text-xs text-gray-300 mt-3">
        Cosine similarity on {players[0] ? Object.keys(players[0].metric_values).length : 0} style metrics
      </p>
    </div>
  );
}
