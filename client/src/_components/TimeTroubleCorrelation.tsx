import { ColumnDef } from '@tanstack/react-table';
import { DashboardPayload } from '../api';
import BaseTable from './BaseTable';

interface TimeTroubleCorrelationProps {
  data: DashboardPayload['metrics'];
  columns: ColumnDef<DashboardPayload['metrics'][number]>[];
}

export default function TimeTroubleCorrelation({
  data,
  columns,
}: TimeTroubleCorrelationProps) {
  if (!data.length) return null;
  return <BaseTable data={data} columns={columns} />;
}
