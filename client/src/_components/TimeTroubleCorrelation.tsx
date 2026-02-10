import { ColumnDef } from '@tanstack/react-table';
import { DashboardPayload } from '../api';
import BaseChart from './BaseChart';
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
  return (
    <BaseChart className="border-0 bg-transparent p-0">
      <BaseTable data={data} columns={columns} />
    </BaseChart>
  );
}
