import MetricCard from './MetricCard';

interface BaseMetricsCardsProps {
  positions: number;
  tactics: number;
  metricsVersion: number;
}

export default function BaseMetricsCards({
  positions,
  tactics,
  metricsVersion,
}: BaseMetricsCardsProps) {
  return (
    <>
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
    </>
  );
}
