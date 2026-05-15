"use client";

export interface RawStats {
  goals?: number;
  assists?: number;
  goals_np?: number;
  goals_assists?: number;
  nineties?: number;
  shots?: number;
  shots_on_target?: number;
  sot_pct?: number;
  fouls_won?: number;
  fouls?: number;
  crosses?: number;
  interceptions?: number;
  yellow_cards?: number;
  red_cards?: number;
  // Multi-source
  xg?: number;
  npxg?: number;
  xa?: number;
  rating?: number;
  index_overall?: number;
  index_offensive?: number;
  index_defensive?: number;
}

interface StatDef {
  type?: "simple";
  key: keyof RawStats;
  label: string;
  format?: (v: number) => string;
  description: string;
}

interface ComparisonDef {
  type: "compare";
  key1: keyof RawStats;  // actual value
  key2: keyof RawStats;  // expected / benchmark value
  label: string;
  format1?: (v: number) => string;  // format for actual
  format2?: (v: number) => string;  // format for expected / delta
  description: string;
}

type AnyDef = StatDef | ComparisonDef;

function fmt(v: number | undefined, decimals = 0): string {
  if (v === undefined || v === null) return "–";
  return decimals > 0 ? v.toFixed(decimals) : String(Math.round(v));
}

function per90(value: number, nineties: number): string {
  if (!nineties) return "–";
  return (value / nineties).toFixed(2);
}

// KPI sets per position group
function getStatDefs(position: string): AnyDef[] {
  const pos = position.toUpperCase();
  const isAttacker  = ["W", "CF", "ST", "SS", "FW", "LW", "RW"].some(p => pos === p || pos.includes(p));
  const isDefender  = ["CB", "LB", "RB", "LWB", "RWB", "GK", "SW"].some(p => pos === p);
  const isMidfield  = ["DM", "CM", "AM", "MF", "LM", "RM", "CAM", "CDM"].some(p => pos === p);

  if (isAttacker) {
    return [
      { type: "compare", key1: "goals", key2: "xg",  label: "G / xG",  format1: v => String(Math.round(v)), format2: v => v.toFixed(1), description: "Goals scored vs expected goals (xG). Green = outperforming, red = underperforming." },
      { type: "compare", key1: "assists", key2: "xa", label: "A / xA", format1: v => String(Math.round(v)), format2: v => v.toFixed(1), description: "Assists vs expected assists (xA). Green = outperforming, red = underperforming." },
      { key: "goals_np",       label: "npG",      format: v => String(Math.round(v)), description: "Non-penalty goals — goals scored excluding penalties" },
      { key: "rating",         label: "Rating",   format: v => v.toFixed(2), description: "Average Sofascore match rating this season" },
      { key: "index_overall",  label: "1vs1",     format: v => v.toFixed(0), description: "One-vs-One overall performance index (0–100)" },
    ];
  }

  if (isMidfield) {
    return [
      { type: "compare", key1: "goals",   key2: "xg",  label: "G / xG",  format1: v => String(Math.round(v)), format2: v => v.toFixed(1), description: "Goals scored vs expected goals (xG)." },
      { type: "compare", key1: "assists", key2: "xa",  label: "A / xA",  format1: v => String(Math.round(v)), format2: v => v.toFixed(1), description: "Assists vs expected assists (xA)." },
      { key: "rating",          label: "Rating",  format: v => v.toFixed(2), description: "Average Sofascore match rating this season" },
      { key: "index_overall",   label: "1vs1",    format: v => v.toFixed(0), description: "One-vs-One overall performance index (0–100)" },
    ];
  }

  if (isDefender) {
    return [
      { key: "goals",             label: "Goals",    description: "Goals scored" },
      { key: "assists",           label: "Assists",  description: "Assists" },
      { key: "interceptions",     label: "Int",      description: "Interceptions this season" },
      { key: "rating",            label: "Rating",   format: v => v.toFixed(2), description: "Average Sofascore match rating" },
      { key: "index_defensive",   label: "Def idx",  format: v => v.toFixed(0), description: "One-vs-One defensive performance index (0–100)" },
      { key: "index_overall",     label: "1vs1",     format: v => v.toFixed(0), description: "One-vs-One overall performance index (0–100)" },
    ];
  }

  // Fallback (GK or unknown)
  return [
    { key: "goals",          label: "Goals",   description: "Goals scored" },
    { key: "assists",        label: "Assists", description: "Assists" },
    { key: "rating",         label: "Rating",  format: v => v.toFixed(2), description: "Average Sofascore match rating" },
    { key: "index_overall",  label: "1vs1",    format: v => v.toFixed(0), description: "One-vs-One overall performance index (0–100)" },
  ];
}

interface Props {
  stats: RawStats;
  position: string;
}

export function KeyStats({ stats, position }: Props) {
  const defs = getStatDefs(position);
  const n90 = stats.nineties ?? 0;

  return (
    <div className="w-full">
      <div className="flex flex-wrap gap-0 border border-gray-100 rounded-lg overflow-hidden">
        {defs.map((def, i) => {
          const borderClass = i > 0 ? "border-l border-gray-100" : "";

          if (def.type === "compare") {
            const actual   = stats[def.key1] as number | undefined;
            const expected = stats[def.key2] as number | undefined;
            if (actual === undefined || actual === null) return null;
            const hasExpected = expected !== undefined && expected !== null;
            const delta = hasExpected ? actual - expected! : null;
            const deltaColor = delta === null ? "" : delta >= 0 ? "text-green-500" : "text-red-500";
            const deltaStr = delta === null ? "" : (delta >= 0 ? "+" : "") + delta.toFixed(1);
            const actualStr  = def.format1 ? def.format1(actual) : String(Math.round(actual));
            const expectedStr = hasExpected && def.format2 ? def.format2(expected!) : hasExpected ? expected!.toFixed(1) : "–";
            return (
              <div
                key={`${String(def.key1)}-${String(def.key2)}`}
                title={def.description}
                className={`flex-1 min-w-[90px] px-4 py-3 flex flex-col items-center text-center
                  ${borderClass} hover:bg-gray-50 transition-colors cursor-default`}
              >
                <span className="text-2xl font-bold text-gray-900 tabular-nums leading-none">
                  {actualStr}
                  {hasExpected && (
                    <span className="text-base font-normal text-gray-400"> / {expectedStr}</span>
                  )}
                </span>
                <span className="text-[10px] text-gray-400 uppercase tracking-wide mt-1 font-medium">
                  {def.label}
                </span>
                {delta !== null && (
                  <span className={`text-[10px] tabular-nums mt-0.5 font-medium ${deltaColor}`}>
                    {deltaStr}
                  </span>
                )}
              </div>
            );
          }

          // Simple stat cell
          const val = stats[def.key];
          if (val === undefined || val === null) return null;
          const display = def.format ? def.format(val as number) : fmt(val as number);
          const noP90 = ["rating", "index_overall", "index_offensive", "index_defensive", "sot_pct", "xg", "xa", "npxg", "goals_np"];
          const p90val = !noP90.includes(def.key as string) && n90 > 0
            ? per90(val as number, n90)
            : null;

          return (
            <div
              key={def.key as string}
              title={def.description}
              className={`flex-1 min-w-[80px] px-4 py-3 flex flex-col items-center text-center
                ${borderClass}
                hover:bg-gray-50 transition-colors group cursor-default`}
            >
              <span className="text-2xl font-bold text-gray-900 tabular-nums leading-none">
                {display}
              </span>
              <span className="text-[10px] text-gray-400 uppercase tracking-wide mt-1 font-medium">
                {def.label}
              </span>
              {p90val && (
                <span className="text-[10px] text-gray-300 tabular-nums mt-0.5 group-hover:text-gray-400 transition-colors">
                  {p90val}/90
                </span>
              )}
            </div>
          );
        })}
      </div>

      {n90 > 0 && (
        <p className="text-[10px] text-gray-400 mt-1.5 text-right">
          {n90.toFixed(1)} × 90 min played · hover for description
        </p>
      )}
    </div>
  );
}

