"use client";

export interface RoleData {
  role: string;
  description: string;
  cluster_id: number;
  similar_players: { name: string; team: string }[];
}

// Colour per role family
const ROLE_COLOURS: Record<string, { bg: string; text: string; border: string }> = {
  "Goal Scorer":          { bg: "bg-amber-50",   text: "text-amber-700",  border: "border-amber-300" },
  "Wide Attacker":        { bg: "bg-teal-50",    text: "text-teal-700",   border: "border-teal-300"  },
  "Dynamic Winger":       { bg: "bg-teal-50",    text: "text-teal-700",   border: "border-teal-300"  },
  "Wide Creator":         { bg: "bg-teal-50",    text: "text-teal-700",   border: "border-teal-300"  },
  "Winger":               { bg: "bg-teal-50",    text: "text-teal-700",   border: "border-teal-300"  },
  "Attacking Fullback":   { bg: "bg-blue-50",    text: "text-blue-700",   border: "border-blue-300"  },
  "Fullback":             { bg: "bg-blue-50",    text: "text-blue-700",   border: "border-blue-300"  },
  "Centre-Back":          { bg: "bg-indigo-50",  text: "text-indigo-700", border: "border-indigo-300"},
  "Ball-playing Defender":{ bg: "bg-indigo-50",  text: "text-indigo-700", border: "border-indigo-300"},
  "Defensive Midfielder": { bg: "bg-violet-50",  text: "text-violet-700", border: "border-violet-300"},
  "Deep-lying Playmaker": { bg: "bg-violet-50",  text: "text-violet-700", border: "border-violet-300"},
};

const DEFAULT_COLOUR = { bg: "bg-gray-50", text: "text-gray-700", border: "border-gray-300" };

interface Props {
  role: RoleData;
}

export function RoleTag({ role }: Props) {
  const col = ROLE_COLOURS[role.role] ?? DEFAULT_COLOUR;

  return (
    <div className={`inline-flex flex-col gap-1.5 rounded-xl border px-4 py-2.5 ${col.bg} ${col.border}`}>
      {/* Role label + description */}
      <div className="flex items-center gap-2">
        <span className={`text-sm font-semibold ${col.text}`}>{role.role}</span>
        <span className="text-xs text-gray-400">·</span>
        <span className="text-xs text-gray-500 leading-tight">{role.description}</span>
      </div>

      {/* Similar players chips */}
      {role.similar_players.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-0.5">
          <span className="text-[10px] text-gray-400 uppercase tracking-wide self-center mr-0.5">
            Similar:
          </span>
          {role.similar_players.map((p) => (
            <span
              key={p.name}
              title={p.team}
              className="inline-flex items-center gap-1 rounded-full bg-white border border-gray-200 px-2.5 py-0.5 text-xs text-gray-600 leading-tight"
            >
              {p.name}
              {p.team && (
                <span className="text-gray-400 text-[10px]">({p.team})</span>
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
