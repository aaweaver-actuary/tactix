import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import MetricsSummaryGrid from './MetricsSummaryGrid';

interface MetricsSummaryCardProps {
  positions: number;
  tactics: number;
  metricsVersion: number;
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function MetricsSummaryCard({
  positions,
  tactics,
  metricsVersion,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: MetricsSummaryCardProps) {
  return (
    <BaseCard
      className="p-4"
      header={
        <h3 className="text-lg font-display text-sand">Metrics summary</h3>
      }
      contentClassName="pt-3"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      <MetricsSummaryGrid
        positions={positions}
        tactics={tactics}
        metricsVersion={metricsVersion}
      />
    </BaseCard>
  );
}
