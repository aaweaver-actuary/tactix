import { ColumnDef } from '@tanstack/react-table';
import { DashboardPayload } from '../api';
import BaseTable from './BaseTable';

interface RecentGamesTableProps {
  data: DashboardPayload['recent_games'];
  columns: ColumnDef<DashboardPayload['recent_games'][number]>[];
  onRowClick?: (row: DashboardPayload['recent_games'][number]) => void;
  rowTestId?: (
    row: DashboardPayload['recent_games'][number],
    index: number,
  ) => string;
}

/**
 * Renders recent games using the shared BaseTable component.
 *
 * @param data - Array of recent game objects.
 * @param columns - Column definitions for the BaseTable.
 */
export default function RecentGamesTable({
  data,
  columns,
  onRowClick,
  rowTestId,
}: RecentGamesTableProps) {
  return (
    <BaseTable
      data={data}
      columns={columns}
      onRowClick={onRowClick}
      rowTestId={rowTestId}
    />
  );
}
