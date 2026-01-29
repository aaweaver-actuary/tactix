import { ColumnDef } from '@tanstack/react-table';
import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import RecentGamesTable from './RecentGamesTable';

interface RecentGamesCardProps {
  data: DashboardPayload['recent_games'];
  columns: ColumnDef<DashboardPayload['recent_games'][number]>[];
  onRowClick?: (row: DashboardPayload['recent_games'][number]) => void;
  rowTestId?: (
    row: DashboardPayload['recent_games'][number],
    index: number,
  ) => string;
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function RecentGamesCard({
  data,
  columns,
  onRowClick,
  rowTestId,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: RecentGamesCardProps) {
  return (
    <BaseCard
      className="p-4"
      data-testid="recent-games-card"
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-display text-sand">Recent games</h3>
          <Badge label="All sources" />
        </div>
      }
      contentClassName="pt-3"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      <RecentGamesTable
        data={data}
        columns={columns}
        onRowClick={onRowClick}
        rowTestId={rowTestId}
      />
    </BaseCard>
  );
}
