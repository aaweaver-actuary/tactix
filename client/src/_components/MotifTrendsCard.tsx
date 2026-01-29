import { ColumnDef } from '@tanstack/react-table';
import type { MetricsTrendsRow } from './MetricsTrends';
import Badge from './Badge';
import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import MetricsTrends from './MetricsTrends';

interface MotifTrendsCardProps {
  data: MetricsTrendsRow[];
  columns: ColumnDef<MetricsTrendsRow>[];
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function MotifTrendsCard({
  data,
  columns,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: MotifTrendsCardProps) {
  return (
    <BaseCard
      className="p-4"
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-display text-sand">Motif trends</h3>
          <Badge label="Rolling 7/30 games" />
        </div>
      }
      contentClassName="pt-3"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      <MetricsTrends data={data} columns={columns} />
    </BaseCard>
  );
}
