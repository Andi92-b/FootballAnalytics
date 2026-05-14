"use client";

import { MetricResult } from "./PizzaChart";

// ── 5-tier bucket system (matching The Athletic) ─────────────────────────────

interface Bucket {
  label: string;
  min: number;
  max: number;
  bg: string;
  text: string;
  barColor: string;
}

const BUCKETS: Bucket[] = [
  { label: "Rare",        min: 81, max: 99, bg: "bg-emerald-50",  text: "text-emerald-700", barColor: "bg-emerald-500" },
  { label: "Good",        min: 61, max: 80, bg: "bg-blue-50",     text: "text-blue-700",    barColor: "bg-blue-400"    },
  { label: "Average",     min: 41, max: 60, bg: "bg-gray-50",     text: "text-gray-500",    barColor: "bg-gray-300"    },
  { label: "Below avg",   min: 21, max: 40, bg: "bg-orange-50",   text: "text-orange-600",  barColor: "bg-orange-300"  },
  { label: "Low",         min: 0,  max: 20, bg: "bg-red-50",      text: "text-red-600",     barColor: "bg-red-300"     },
];

function getBucket(percentile: number): Bucket {
  return BUCKETS.find((b) => percentile >= b.min && percentile <= b.max) ?? BUCKETS[2];
}

// ── Category config ───────────────────────────────────────────────────────────

const CATEGORY_ORDER = ["Defence", "Possession", "Progression", "Attack"];
const CATEGORY_COLORS: Record<string, string> = {
  Defence:    "text-blue-700",
  Possession: "text-teal-700",
  Progression:"text-purple-700",
  Attack:     "text-red-600",
};

// ── Component ─────────────────────────────────────────────────────────────────

export interface StyleSummaryProps {
  metrics: MetricResult[];
  position: string;
}

export function StyleSummary({ metrics, position }: StyleSummaryProps) {
  if (metrics.length === 0) return null;

  // Group by category in canonical order
  const grouped = CATEGORY_ORDER.reduce<Record<string, MetricResult[]>>((acc, cat) => {
    const group = metrics.filter((m) => m.category === cat);
    if (group.length > 0) acc[cat] = group;
    return acc;
  }, {});

  return (
    <div className="w-full">
      <div className="flex items-baseline gap-2 mb-4">
        <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">Playing Style</h2>
        <span className="text-xs text-gray-400">{position} · percentile vs peers</span>
      </div>

      <div className="space-y-5">
        {Object.entries(grouped).map(([cat, catMetrics]) => (
          <div key={cat}>
            <p className={`text-xs font-semibold uppercase tracking-wider mb-2 ${CATEGORY_COLORS[cat] ?? "text-gray-500"}`}>
              {cat}
            </p>
            <div className="space-y-2">
              {catMetrics.map((m) => {
                const bucket = getBucket(m.percentile);
                const barWidth = `${m.percentile}%`;
                return (
                  <div key={m.name} className="grid grid-cols-[1fr_auto] items-center gap-3">
                    {/* Left: label + bar */}
                    <div>
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-xs text-gray-700 font-medium">{m.name}</span>
                        <span className={`text-xs font-semibold ${bucket.text}`}>{m.percentile}</span>
                      </div>
                      <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${bucket.barColor}`}
                          style={{ width: barWidth }}
                        />
                      </div>
                    </div>
                    {/* Right: tier badge */}
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${bucket.bg} ${bucket.text}`}>
                      {bucket.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-5 pt-4 border-t border-gray-100">
        {BUCKETS.map((b) => (
          <span key={b.label} className="flex items-center gap-1 text-xs text-gray-400">
            <span className={`inline-block w-2 h-2 rounded-full ${b.barColor}`} />
            {b.label} ({b.min}–{b.max})
          </span>
        ))}
      </div>
    </div>
  );
}
