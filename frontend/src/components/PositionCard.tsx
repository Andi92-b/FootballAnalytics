"use client";

export interface PlayingTimeData {
  pos: string;
  mp: number;
  minutes: number;
  min_pct: number;
  starts: number;
  mins_per_start: number;
  complete_games: number;
  subs: number;
  mins_per_sub: number;
  unsubbed: number;
}

interface Props {
  playingTime: PlayingTimeData;
  player: string;
}

// ── Position coordinates on a 200×300 pitch (cx/cy as absolute px) ───────────
// Pitch is rendered portrait: own goal at bottom, attack direction upward.
// Coordinates place each position at its typical zone center.
const POS_COORDS: Record<string, { cx: number; cy: number; label: string }> = {
  GK:  { cx: 100, cy: 274, label: "GK" },
  DF:  { cx: 100, cy: 228, label: "DF" },
  CB:  { cx: 100, cy: 228, label: "CB" },
  LB:  { cx:  42, cy: 220, label: "LB" },
  RB:  { cx: 158, cy: 220, label: "RB" },
  LWB: { cx:  36, cy: 196, label: "LWB" },
  RWB: { cx: 164, cy: 196, label: "RWB" },
  DM:  { cx: 100, cy: 190, label: "DM" },
  CDM: { cx: 100, cy: 190, label: "CDM" },
  MF:  { cx: 100, cy: 158, label: "MF" },
  CM:  { cx: 100, cy: 158, label: "CM" },
  LM:  { cx:  44, cy: 158, label: "LM" },
  RM:  { cx: 156, cy: 158, label: "RM" },
  AM:  { cx: 100, cy: 122, label: "AM" },
  CAM: { cx: 100, cy: 122, label: "CAM" },
  LW:  { cx:  40, cy: 110, label: "LW" },
  RW:  { cx: 160, cy: 110, label: "RW" },
  FW:  { cx: 100, cy:  88, label: "FW" },
  CF:  { cx: 100, cy:  80, label: "CF" },
  ST:  { cx: 100, cy:  72, label: "ST" },
  SS:  { cx: 100, cy:  96, label: "SS" },
};

// Estimate % split from ordered FBref pos string e.g. "FW,MF" → [{FW,65},{MF,35}]
function positionWeights(pos: string): Array<{ key: string; pct: number }> {
  if (!pos) return [];
  const parts = pos.split(",").map((p) => p.trim().toUpperCase()).filter((p) => p in POS_COORDS);
  if (parts.length === 0) return [];
  // Descending weights: 1st gets bulk of time, remainder shared
  const WEIGHTS: Record<number, number[]> = {
    1: [100],
    2: [65, 35],
    3: [55, 33, 12],
    4: [48, 28, 16, 8],
  };
  const w = WEIGHTS[Math.min(parts.length, 4)] ?? parts.map((_, i) => Math.max(5, 50 - i * 15));
  return parts.map((key, i) => ({ key, pct: w[i] ?? 5 }));
}

// Bubble radius: primary ≈ 28px, secondary ≈ 22px, tertiary ≈ 16px
function bubbleRadius(rank: number): number {
  return [28, 22, 16, 12][rank] ?? 11;
}

// Color based on pct: dark red → light red (The Athletic palette)
function bubbleColor(pct: number): { fill: string; text: string } {
  if (pct >= 55) return { fill: "#c0392b", text: "#fff" };
  if (pct >= 30) return { fill: "#e05c52", text: "#fff" };
  if (pct >= 12) return { fill: "#f0a099", text: "#333" };
  return { fill: "#f8d5d2", text: "#555" };
}

// ── Circular progress (donut) ─────────────────────────────────────────────────
function DonutRing({ value, max, size = 64, stroke = 7, color = "#3b82f6" }: {
  value: number; max: number; size?: number; stroke?: number; color?: string;
}) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(1, value / Math.max(max, 1));
  const dash = pct * circ;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={stroke} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color}
        strokeWidth={stroke} strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
    </svg>
  );
}

function Bar({ value, max, color = "#3b82f6" }: { value: number; max: number; color?: string }) {
  const pct = Math.min(100, Math.round((value / Math.max(max, 1)) * 100));
  return (
    <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

export function PositionCard({ playingTime: pt, player }: Props) {
  const posEntries = positionWeights(pt.pos);
  const SEASON_MINUTES = 3420;
  const startPct = pt.mp > 0 ? Math.round((pt.starts / pt.mp) * 100) : 0;
  const completePct = pt.starts > 0 ? Math.round((pt.complete_games / pt.starts) * 100) : 0;

  // Pitch dimensions
  const W = 200, H = 300;
  const PAD = 10;

  return (
    <div className="w-full">
      <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide mb-4">
        Position &amp; Playing Time
      </h2>

      <div className="flex flex-row gap-8 items-start">
        {/* ── Pitch + position bubbles ── */}
        <div className="shrink-0 flex flex-col items-center">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            width={160}
            height={240}
            style={{ fontFamily: "inherit" }}
          >
            {/* Pitch background */}
            <rect x={0} y={0} width={W} height={H} rx={4} fill="#f5f0e8" />

            {/* Pitch outline */}
            <rect x={PAD} y={PAD} width={W - 2 * PAD} height={H - 2 * PAD}
              fill="none" stroke="#c8bfa8" strokeWidth={1.2} />

            {/* Halfway line */}
            <line x1={PAD} y1={H / 2} x2={W - PAD} y2={H / 2}
              stroke="#c8bfa8" strokeWidth={1} />

            {/* Centre circle */}
            <circle cx={W / 2} cy={H / 2} r={28}
              fill="none" stroke="#c8bfa8" strokeWidth={1} />
            <circle cx={W / 2} cy={H / 2} r={1.5} fill="#c8bfa8" />

            {/* Top penalty area (opponent) */}
            <rect x={52} y={PAD} width={96} height={48}
              fill="none" stroke="#c8bfa8" strokeWidth={1} />
            {/* Top 6-yard box */}
            <rect x={74} y={PAD} width={52} height={20}
              fill="none" stroke="#c8bfa8" strokeWidth={0.8} />
            {/* Top penalty spot */}
            <circle cx={W / 2} cy={PAD + 38} r={1.5} fill="#c8bfa8" />
            {/* Top penalty arc */}
            <path d={`M 70 ${PAD + 48} A 20 20 0 0 1 130 ${PAD + 48}`}
              fill="none" stroke="#c8bfa8" strokeWidth={1} />

            {/* Bottom penalty area (own goal) */}
            <rect x={52} y={H - PAD - 48} width={96} height={48}
              fill="none" stroke="#c8bfa8" strokeWidth={1} />
            {/* Bottom 6-yard box */}
            <rect x={74} y={H - PAD - 20} width={52} height={20}
              fill="none" stroke="#c8bfa8" strokeWidth={0.8} />
            {/* Bottom penalty spot */}
            <circle cx={W / 2} cy={H - PAD - 38} r={1.5} fill="#c8bfa8" />
            {/* Bottom penalty arc */}
            <path d={`M 70 ${H - PAD - 48} A 20 20 0 0 0 130 ${H - PAD - 48}`}
              fill="none" stroke="#c8bfa8" strokeWidth={1} />

            {/* Goals */}
            <rect x={82} y={PAD - 7} width={36} height={7}
              fill="none" stroke="#c8bfa8" strokeWidth={1} />
            <rect x={82} y={H - PAD} width={36} height={7}
              fill="none" stroke="#c8bfa8" strokeWidth={1} />

            {/* Attack direction arrow */}
            <line x1={6} y1={H * 0.65} x2={6} y2={H * 0.35}
              stroke="#aaa" strokeWidth={1} />
            <polygon points={`3,${H * 0.35} 9,${H * 0.35} 6,${H * 0.35 - 6}`}
              fill="#aaa" />

            {/* Position bubbles */}
            {posEntries.map(({ key, pct }, rank) => {
              const pos = POS_COORDS[key];
              if (!pos) return null;
              const r = bubbleRadius(rank);
              const { fill, text } = bubbleColor(pct);
              const labelW = pos.label.length <= 2 ? 22 : 28;
              return (
                <g key={key}>
                  {/* Shadow */}
                  <circle cx={pos.cx} cy={pos.cy} r={r + 1.5} fill="rgba(0,0,0,0.08)" />
                  {/* Bubble */}
                  <circle cx={pos.cx} cy={pos.cy} r={r} fill={fill} />
                  {/* Percentage text */}
                  <text
                    x={pos.cx} y={pos.cy + 4}
                    textAnchor="middle"
                    fontSize={r >= 26 ? 11 : r >= 20 ? 10 : 9}
                    fontWeight="700"
                    fill={text}
                  >
                    {pct}%
                  </text>
                  {/* Label box below bubble */}
                  <rect
                    x={pos.cx - labelW / 2} y={pos.cy + r + 3}
                    width={labelW} height={13}
                    rx={2}
                    fill="#fff"
                    stroke="#c8bfa8"
                    strokeWidth={0.8}
                  />
                  <text
                    x={pos.cx} y={pos.cy + r + 12}
                    textAnchor="middle"
                    fontSize={8}
                    fontWeight="600"
                    fill="#333"
                    letterSpacing={0.3}
                  >
                    {pos.label}
                  </text>
                </g>
              );
            })}
          </svg>
          <p className="text-[10px] text-gray-400 mt-1">Positions played</p>
        </div>

        {/* ── Stats panel ── */}
        <div className="flex-1 grid grid-cols-2 gap-x-6 gap-y-5">
          {/* Minutes bar */}
          <div className="col-span-2">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-gray-500">Minutes played</span>
              <span className="text-xs font-semibold text-gray-800">
                {pt.minutes.toLocaleString()}
                <span className="font-normal text-gray-400"> / {SEASON_MINUTES}</span>
              </span>
            </div>
            <Bar value={pt.minutes} max={SEASON_MINUTES} color="#e05c52" />
            <p className="text-[10px] text-gray-400 mt-1">
              {pt.min_pct}% of available minutes · {pt.mp} appearances
            </p>
          </div>

          {/* Starts donut */}
          <div className="flex items-center gap-3">
            <div className="relative shrink-0">
              <DonutRing value={pt.starts} max={pt.mp} size={56} stroke={6} color="#10b981" />
              <span className="absolute inset-0 flex items-center justify-center text-[11px] font-bold text-gray-700">
                {startPct}%
              </span>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-800">{pt.starts} starts</p>
              <p className="text-[10px] text-gray-400">avg {pt.mins_per_start} min</p>
            </div>
          </div>

          {/* Complete games donut */}
          <div className="flex items-center gap-3">
            <div className="relative shrink-0">
              <DonutRing value={pt.complete_games} max={pt.starts || 1} size={56} stroke={6} color="#8b5cf6" />
              <span className="absolute inset-0 flex items-center justify-center text-[11px] font-bold text-gray-700">
                {completePct}%
              </span>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-800">{pt.complete_games} full 90s</p>
              <p className="text-[10px] text-gray-400">of {pt.starts} starts</p>
            </div>
          </div>

          {/* Subs row */}
          <div className="col-span-2 flex items-center gap-5 pt-2 border-t border-gray-100">
            <div title="Number of appearances as a substitute — games where the player came on from the bench">
              <p className="text-sm font-bold text-gray-800">{pt.subs}</p>
              <p className="text-[10px] text-gray-400">Sub appearances</p>
            </div>
            {pt.subs > 0 && (
              <>
                <div title="Average minutes played per substitute appearance">
                  <p className="text-sm font-bold text-gray-800">{pt.mins_per_sub}'</p>
                  <p className="text-[10px] text-gray-400">Avg min as sub</p>
                </div>
                <div title="Games where the player was not substituted off — stayed on until the final whistle">
                  <p className="text-sm font-bold text-gray-800">{pt.unsubbed}</p>
                  <p className="text-[10px] text-gray-400">Stayed until end</p>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
