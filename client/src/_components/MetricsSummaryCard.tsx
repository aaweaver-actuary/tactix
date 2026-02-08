import BaseCard, { BaseCardDragProps } from './BaseCard';
import MetricsSummaryGrid from './MetricsSummaryGrid';

interface MetricsSummaryCardProps extends BaseCardDragProps {
  positions: number;
  tactics: number;
  metricsVersion: number;
}

export default function MetricsSummaryCard({
  positions,
  tactics,
  metricsVersion,
  ...dragProps
}: MetricsSummaryCardProps) {
  return (
    <BaseCard
      className="p-4"
      header={
        <h3 className="text-lg font-display text-sand">Metrics summary</h3>
      }
      contentClassName="pt-3"
      {...dragProps}
    >
      <MetricsSummaryGrid
        positions={positions}
        tactics={tactics}
        metricsVersion={metricsVersion}
      />
    </BaseCard>
  );
}
