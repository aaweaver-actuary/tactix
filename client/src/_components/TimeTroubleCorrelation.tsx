import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseCard from './BaseCard';

interface TimeTroubleCorrelationProps {
  metricsData: DashboardPayload['metrics'];
}

const formatCorrelation = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  const rounded = value.toFixed(2);
  return value > 0 ? `+${rounded}` : rounded;
};

const formatRate = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  return `${(value * 100).toFixed(1)}%`;
};

export default function TimeTroubleCorrelation({
  metricsData,
}: TimeTroubleCorrelationProps) {
  if (!metricsData.length) return null;

  const rows = [...metricsData].sort((a, b) => {
    const left = a.time_control ?? 'unknown';
    const right = b.time_control ?? 'unknown';
    return left.localeCompare(right);
  });

  const header = (
    <div className="flex items-center justify-between">
      <h3 className="text-lg font-display text-sand">
        Time-trouble correlation
      </h3>
      <Badge label="By time control" />
    </div>
  );

  return (
    <BaseCard
      className="p-4"
      data-testid="time-trouble-correlation"
      header={header}
      contentClassName="pt-3"
    >
      <p className="text-xs text-sand/70 mb-3">
        Correlation between time trouble (≤30s or ≤10% of the initial clock) and
        missed tactics. Positive values indicate more misses in time trouble.
      </p>
      <div className="overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="text-sand/70">
            <tr>
              <th className="text-left py-2 pr-3">Time control</th>
              <th className="text-left py-2 pr-3">Correlation</th>
              <th className="text-left py-2 pr-3">Time trouble rate</th>
              <th className="text-left py-2 pr-3">Samples</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.time_control} className="border-t border-sand/10">
                <td className="py-2 pr-3 text-sand">
                  {row.time_control ?? 'unknown'}
                </td>
                <td className="py-2 pr-3 text-sand">
                  {formatCorrelation(row.found_rate)}
                </td>
                <td className="py-2 pr-3 text-sand">
                  {formatRate(row.miss_rate)}
                </td>
                <td className="py-2 pr-3 text-sand/80">{row.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </BaseCard>
  );
}
