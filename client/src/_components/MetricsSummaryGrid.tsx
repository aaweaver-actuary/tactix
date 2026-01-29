import MetricCard from './MetricCard';

interface MetricsSummaryGridProps {
  positions: number;
  tactics: number;
  metricsVersion: number;
}

export default function MetricsSummaryGrid({
  positions,
  tactics,
  metricsVersion,
}: MetricsSummaryGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <MetricCard
        title="Positions"
        value={`${positions}`}
        note="Captured when you were to move"
      />
      <MetricCard
        title="Tactics"
        value={`${tactics}`}
        note="Analyzed via Stockfish"
      />
      <MetricCard
        title="Metrics ver."
        value={`${metricsVersion}`}
        note="Cache bust signal"
      />
    </div>
  );
}
