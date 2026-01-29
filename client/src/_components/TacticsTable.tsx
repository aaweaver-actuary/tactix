import { ColumnDef } from '@tanstack/react-table';
import { DashboardPayload } from '../api';
import BaseTable from './BaseTable';

interface TacticsTableProps {
  data: DashboardPayload['tactics'];
  columns: ColumnDef<DashboardPayload['tactics'][number]>[];
  onRowClick?: (row: DashboardPayload['tactics'][number]) => void;
  rowTestId?: (
    row: DashboardPayload['tactics'][number],
    index: number,
  ) => string;
}

/**
 * Renders recent tactics using the shared BaseTable component.
 *
 * @param data - Array of tactic objects.
 * @param columns - Column definitions for the BaseTable.
 */
export default function TacticsTable({
  data,
  columns,
  onRowClick,
  rowTestId,
}: TacticsTableProps) {
  return (
    <BaseTable
      data={data}
      columns={columns}
      onRowClick={onRowClick}
      rowTestId={rowTestId}
    />
  );
}
