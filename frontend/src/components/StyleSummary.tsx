"use client";

import { MetricResult } from "./PizzaChart";
import { METRIC_DESCRIPTIONS } from "@/lib/metricDescriptions";

// ── 5-tier bucket system ──────────────────────────────────────────────────────

interface Bucket {
  label: string;
  min: number;
  max: number;
  bg: string;
  text: string;
  dot: string;
}

const BUCKETS: Bucket[] = [
  { label: "Rare",       min: 81, max: 99, bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  { label: "Good",       min: 61, max: 80, bg: "bg-blue-50",    text: "text-blue-700",    dot: "bg-blue-400"   },
  { label: "Average",    min: 41, max: 60, bg: "bg-gray-100",   text: "text-gray-500",    dot: "bg-gray-300"   },
  { label: "Below avg",  min: 21, max: 40, bg: "bg-orange-50",  text: "text-orange-600",  dot: "bg-orange-300" },
  { label: "Low",        min: 0,  max: 20, bg: "bg-red-50",     text: "text-red-600",     dot: "bg-red-300"    },
];

function getBucket(percentile: number): Bucket {
  return BUCKETS.find((b) => percentile >= b.min && percentile <= b.max) ?? BUCKETS[2];
}

// ── Category config ───────────────────────────────────────────────────────────

const CATEGORY_ORDER = ["Defence", "Possession", "Progression", "Attack"];
const CATEGORY_COLORS: Record<string, string> = {
  Defence:     "text-blue-700",
  Possession:  "text-teal-700",
  Progression: "text-purple-700",
  Attack:      "text-red-600",
};

// ── Component ─────────────────────────────────────────────────────────────────

export interface StyleSummaryProps {
  metrics: MetricResult[];
  position: string;
}

export function StyleSummary({ metrics, position }: StyleSummaryProps) {
  if (metrics.length === 0) return null;

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
            <p className={`text-xs font-semibold uppercase tracking-wider mb-1.5 ${CATEGORY_COLORS[cat] ?? "text-gray-500"}`}>
              {cat}
            </p>
            <div className="space-y-1">
              {catMetrics.map((m) => {
                const bucket = getBucket(m.percentile);
                const description = METRIC_DESCRIPTIONS[m.name];
                return (
                  <div
                    key={m.name}
                    className="flex items-center justify-between gap-3 px-2 py-1.5 rounded-md hover:bg-gray-50 transition-colors"
                  >
                    {/* Metric name with tooltip */}
                    <div className="relative group flex-1 min-w-0">
                      <span className="text-xs text-gray-600 truncate flex items-center gap-1 cursor-default">
                        {m.name}
                        {description && (
                          <span className="text-gray-300 text-[10px] leading-none">ⓘ</span>
                        )}
                      </span>
                      {description && (
                        <div className="absolute left-0 top-full mt-1 z-20 hidden group-hover:block w-64 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl pointer-events-none">
                          <p className="font-semibold mb-0.5 text-gray-200">{m.name}</p>
                          <p className="text-gray-400 leading-snug">{description}</p>
                          <div className="absolute -top-1.5 left-3 w-2.5 h-2.5 bg-gray-900 rotate-45" />
                        </div>
                      )}
                    </div>
                    <span className={`text-xs font-bold tabular-nums shrink-0 ${bucket.text}`}>{m.percentile}</span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full whitespace-nowrap shrink-0 ${bucket.bg} ${bucket.text}`}>
                      {bucket.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
