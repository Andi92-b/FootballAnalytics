// PizzaChart component — designed by Claude Design (design-handoff skill)
// Placeholder until GATE: DESIGN is complete.

import { useRef, useEffect } from "react";

export interface MetricResult {
  name: string;
  category: "Defence" | "Possession" | "Progression" | "Attack";
  raw: number;
  percentile: number;
  source: string;
}

export interface PizzaChartProps {
  svg: string;
  player: string;
  position: string;
  season: string;
  league: string;
  metrics: MetricResult[];
  missingMetrics: string[];
  dataSources: string[];
  isLoading: boolean;
  error: string | null;
  selectedMetric?: string | null;
  onMetricClick?: (metricName: string) => void;
}

export function PizzaChart({
  isLoading, error, svg, player, position, season,
  missingMetrics, dataSources, metrics, selectedMetric, onMetricClick,
}: PizzaChartProps) {
  const svgRef = useRef<HTMLDivElement>(null);

  // After the SVG renders, find text labels matching metric names and make them clickable
  useEffect(() => {
    if (!svgRef.current || !onMetricClick || metrics.length === 0) return;

    const metricNames = new Set(metrics.map((m) => m.name.trim().toLowerCase()));
    const textEls = svgRef.current.querySelectorAll<SVGTextElement>("text");

    textEls.forEach((el) => {
      const label = el.textContent?.trim().toLowerCase() ?? "";
      if (!metricNames.has(label)) return;

      const canonical = metrics.find((m) => m.name.trim().toLowerCase() === label)!.name;
      el.style.cursor = "pointer";
      el.style.userSelect = "none";

      // Highlight selected metric label
      if (selectedMetric && selectedMetric.trim().toLowerCase() === label) {
        el.style.fontWeight = "bold";
        el.style.opacity = "1";
      } else {
        el.style.fontWeight = "";
        el.style.opacity = "";
      }

      const handler = (e: Event) => {
        e.stopPropagation();
        onMetricClick(canonical);
      };
      el.removeEventListener("click", handler); // avoid duplicate listeners on re-render
      el.addEventListener("click", handler);
    });
  }, [svg, metrics, selectedMetric, onMetricClick]);

  if (isLoading) return <div aria-live="polite" aria-busy className="text-gray-400">Loading…</div>;
  if (error) return <div className="text-red-600">{error}</div>;
  if (!svg) return <div className="text-gray-400">Search for a player above</div>;

  return (
    <figure role="img" aria-label={`${player} pizza chart`} className="max-w-[600px] w-full mx-auto">
      <div ref={svgRef} dangerouslySetInnerHTML={{ __html: svg }} />
      <figcaption className="text-sm text-gray-500 text-center mt-2">
        {player} · {position} · {season}
        {onMetricClick && (
          <span className="ml-2 text-xs text-gray-300">· click a label to compare</span>
        )}
        {dataSources.length > 0 && (
          <span className="ml-2 text-xs text-gray-400">sources: {dataSources.join(" + ")}</span>
        )}
      </figcaption>
      {missingMetrics.length > 0 && (
        <p className="text-xs text-gray-400 text-center mt-1">
          {missingMetrics.length} metric{missingMetrics.length !== 1 ? "s" : ""} unavailable: {missingMetrics.join(", ")}
        </p>
      )}
    </figure>
  );
}
