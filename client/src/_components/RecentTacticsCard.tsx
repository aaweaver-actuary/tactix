import { ColumnDef } from '@tanstack/react-table';
import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import TacticsTable from './TacticsTable';

interface RecentTacticsCardProps {
  data: DashboardPayload['tactics'];
  columns: ColumnDef<DashboardPayload['tactics'][number]>[];
  onRowClick?: (row: DashboardPayload['tactics'][number]) => void;
  rowTestId?: (row: DashboardPayload['tactics'][number]) => string;
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function RecentTacticsCard({
  data,
  columns,
  onRowClick,
  rowTestId,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: RecentTacticsCardProps) {
  return (
    <BaseCard
      className="p-4"
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-display text-sand">Recent tactics</h3>
          <Badge label="Live" />
        </div>
      }
      contentClassName="pt-3"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      <TacticsTable
        data={data}
        columns={columns}
        onRowClick={onRowClick}
        rowTestId={rowTestId}
      />
    </BaseCard>
  );
}
