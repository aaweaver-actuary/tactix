import { ColumnDef } from '@tanstack/react-table';
import type { MetricsTrendsRow } from './MetricsTrends';
import Badge from './Badge';
import BaseCard, { BaseCardDragProps } from './BaseCard';
import MetricsTrends from './MetricsTrends';

interface MotifTrendsCardProps extends BaseCardDragProps {
  data: MetricsTrendsRow[];
  columns: ColumnDef<MetricsTrendsRow>[];
}

export default function MotifTrendsCard({
  data,
  columns,
  ...dragProps
}: MotifTrendsCardProps) {
  return (
    <BaseCard
      className="p-4"
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-display text-sand">Motif trends</h3>
          <Badge label="Rolling 7/30 days" />
        </div>
      }
      contentClassName="pt-3"
      {...dragProps}
    >
      <MetricsTrends data={data} columns={columns} />
    </BaseCard>
  );
}
