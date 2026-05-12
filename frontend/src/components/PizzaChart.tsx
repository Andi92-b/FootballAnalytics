// PizzaChart component — designed by Claude Design (design-handoff skill)
// Placeholder until GATE: DESIGN is complete.

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
}

export function PizzaChart({ isLoading, error, svg, player, position, season, missingMetrics, dataSources }: PizzaChartProps) {
  if (isLoading) return <div aria-live="polite" aria-busy className="text-gray-400">Loading…</div>;
  if (error) return <div className="text-red-600">{error}</div>;
  if (!svg) return <div className="text-gray-400">Search for a player above</div>;

  return (
    <figure role="img" aria-label={`${player} pizza chart`} className="max-w-[600px] w-full mx-auto">
      <div dangerouslySetInnerHTML={{ __html: svg }} />
      <figcaption className="text-sm text-gray-500 text-center mt-2">
        {player} · {position} · {season}
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
