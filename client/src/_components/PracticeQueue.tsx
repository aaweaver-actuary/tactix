import { ColumnDef } from '@tanstack/react-table';
import { PracticeQueueItem } from '../api';
import BaseTable from './BaseTable';

interface PracticeQueueProps {
  data: PracticeQueueItem[] | null;
  columns: ColumnDef<PracticeQueueItem>[];
  onRowClick?: (row: PracticeQueueItem) => void;
}

/**
 * Renders the practice queue table using the shared BaseTable component.
 *
 * @param data - Practice queue items, or null while loading.
 * @param columns - Column definitions for the BaseTable.
 */
export default function PracticeQueue({
  data,
  columns,
  onRowClick,
}: PracticeQueueProps) {
  return <BaseTable data={data} columns={columns} onRowClick={onRowClick} />;
}
