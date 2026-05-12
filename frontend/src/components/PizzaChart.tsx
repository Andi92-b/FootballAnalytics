// PizzaChart component — designed by Claude Design (design-handoff skill)
// Placeholder until GATE: DESIGN is complete.

export interface MetricResult {
  name: string;
  category: "Defence" | "Possession" | "Progression" | "Attack";
  raw: number;
  percentile: number;
}

export interface PizzaChartProps {
  svg: string;
  player: string;
  position: string;
  season: string;
  league: string;
  metrics: MetricResult[];
  isLoading: boolean;
  error: string | null;
}

export function PizzaChart({ isLoading, error, svg, player, position, season }: PizzaChartProps) {
  if (isLoading) return <div aria-live="polite" aria-busy className="text-gray-400">Loading…</div>;
  if (error) return <div className="text-red-600">{error}</div>;
  if (!svg) return <div className="text-gray-400">Search for a player above</div>;

  return (
    <figure role="img" aria-label={`${player} pizza chart`} className="max-w-[600px] w-full mx-auto">
      <div dangerouslySetInnerHTML={{ __html: svg }} />
      <figcaption className="text-sm text-gray-500 text-center mt-2">
        {player} · {position} · {season}
      </figcaption>
    </figure>
  );
}
