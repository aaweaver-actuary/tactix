import { ColumnDef } from '@tanstack/react-table';
import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import TimeTroubleCorrelation from './TimeTroubleCorrelation';

interface TimeTroubleCorrelationCardProps {
  data: DashboardPayload['metrics'];
  columns: ColumnDef<DashboardPayload['metrics'][number]>[];
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function TimeTroubleCorrelationCard({
  data,
  columns,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: TimeTroubleCorrelationCardProps) {
  return (
    <BaseCard
      className="p-4"
      data-testid="time-trouble-correlation"
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-display text-sand">
            Time-trouble correlation
          </h3>
          <Badge label="By time control" />
        </div>
      }
      contentClassName="pt-3"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      <p className="text-xs text-sand/70 mb-3">
        Correlation between time trouble (≤30s or ≤10% of the initial clock) and
        missed tactics. Positive values indicate more misses in time trouble.
      </p>
      <TimeTroubleCorrelation data={data} columns={columns} />
    </BaseCard>
  );
}
