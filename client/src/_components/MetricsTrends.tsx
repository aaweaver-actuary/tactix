import { ColumnDef } from '@tanstack/react-table';
import { DashboardPayload } from '../api';
import BaseTable from './BaseTable';

export type MetricsTrendsRow = {
  motif: string;
  seven?: DashboardPayload['metrics'][number];
  thirty?: DashboardPayload['metrics'][number];
};

interface MetricsTrendsProps {
  data: MetricsTrendsRow[];
  columns: ColumnDef<MetricsTrendsRow>[];
}

/**
 * Renders a motif trends table using the shared BaseTable component.
 *
 * @param data - Prepared motif trend rows (latest per motif).
 * @param columns - Column definitions for the BaseTable.
 */
export default function MetricsTrends({ data, columns }: MetricsTrendsProps) {
  if (!data.length) return null;
  return <BaseTable data={data} columns={columns} />;
}
