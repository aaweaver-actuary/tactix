import BaseCard, { BaseCardDragProps } from './BaseCard';
import MetricsSummaryGrid from './MetricsSummaryGrid';
import { DashboardPayload } from '../api';

interface MetricsSummaryCardProps extends BaseCardDragProps {
  positions: number;
  tactics: number;
  metricsVersion: number;
  sourceSync?: DashboardPayload['source_sync'];
}

export default function MetricsSummaryCard({
  positions,
  tactics,
  metricsVersion,
  sourceSync,
  ...dragProps
}: MetricsSummaryCardProps) {
  return (
    <BaseCard
      className="p-4"
      defaultCollapsed={false}
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
        sourceSync={sourceSync}
      />
    </BaseCard>
  );
}
