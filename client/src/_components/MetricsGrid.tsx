import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseCard from './BaseCard';
import MetricCard from './MetricCard';

interface MetricsGridProps {
  metricsData: DashboardPayload['metrics'];
}

/**
 * Renders a grid of metric cards displaying motif breakdown data.
 *
 * @param metricsData - An array of metric objects containing motif statistics.
 * @returns A React component displaying the motif breakdown in a card layout.
 *
 * @remarks
 * Each metric card shows the motif name, the number of found and total motifs,
 * and a note with missed and failed attempt counts.
 *
 * @example
 * <MetricsGrid metricsData={[
 *   { motif: 'Motif A', found: 5, total: 10, missed: 3, failed_attempt: 2 },
 *   { motif: 'Motif B', found: 8, total: 12, missed: 2, failed_attempt: 2 }
 * ]} />
 */
export default function MetricsGrid({ metricsData }: MetricsGridProps) {
  const header = (
    <div className="flex items-center justify-between">
      <h3 className="text-lg font-display text-sand">Motif breakdown</h3>
      <Badge label="Updated" />
    </div>
  );

  return (
    <BaseCard
      className="p-4"
      data-testid="motif-breakdown"
      header={header}
      contentClassName="pt-3"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {metricsData.map((row) => (
          <MetricCard
            key={row.motif}
            title={row.motif}
            value={`${row.found}/${row.total}`}
            note={`${row.missed} missed, ${row.failed_attempt} failed`}
          />
        ))}
      </div>
    </BaseCard>
  );
}
