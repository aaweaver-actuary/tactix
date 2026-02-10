import { ColumnDef } from '@tanstack/react-table';
import { DashboardPayload } from '../api';
import BaseChart from './BaseChart';
import BaseTable from './BaseTable';

export type MetricsTrendsRow = {
  motif: string;
  seven?: DashboardPayload['metrics'][number];
  thirty?: DashboardPayload['metrics'][number];
};

interface MetricsTrendsProps {
  data: MetricsTrendsRow[] | null;
  columns: ColumnDef<MetricsTrendsRow>[];
}

/**
 * Renders a motif trends table using the shared BaseTable component.
 *
 * @param data - Prepared motif trend rows (latest per motif).
 * @param columns - Column definitions for the BaseTable.
 */
export default function MetricsTrends({ data, columns }: MetricsTrendsProps) {
  return (
    <BaseChart
      testId="motif-trends-table"
      className="border-0 bg-transparent p-0"
    >
      <BaseTable data={data} columns={columns} />
    </BaseChart>
  );
}
