import { useMemo } from 'react';
import { DashboardPayload } from '../api';
import Badge from './Badge';

interface MetricsTrendsProps {
  metricsData: DashboardPayload['metrics'];
}

/**
 * Displays a table of motif trends based on the latest available metrics data.
 *
 * For each motif, shows the most recent 7-game and 30-game trend metrics, including
 * the found rate (as a percentage) and the last update date. Only metrics with
 * `metric_type` of `'trend'` and a valid `trend_date` are considered.
 *
 * @param metricsData - Array of metric objects containing trend data for motifs.
 * @returns A card component with a table of motif trends, or `null` if no data is available.
 */
export default function MetricsTrends({ metricsData }: MetricsTrendsProps) {
  const latestByMotif = useMemo(() => {
    const map = new Map<
      string,
      {
        seven?: DashboardPayload['metrics'][number];
        thirty?: DashboardPayload['metrics'][number];
      }
    >();
    metricsData.forEach((row) => {
      if (row.metric_type !== 'trend' || !row.trend_date) return;
      const current = map.get(row.motif) || {};
      const isSeven = row.window_days === 7;
      const slot = isSeven ? 'seven' : row.window_days === 30 ? 'thirty' : null;
      if (!slot) return;
      const existing = current[slot];
      if (
        !existing ||
        new Date(row.trend_date) > new Date(existing.trend_date || 0)
      ) {
        current[slot] = row;
      }
      map.set(row.motif, current);
    });
    return Array.from(map.entries()).map(([motif, value]) => ({
      motif,
      ...value,
    }));
  }, [metricsData]);

  if (!latestByMotif.length) return null;

  const formatPercent = (value: number | null) =>
    value === null || Number.isNaN(value)
      ? '--'
      : `${(value * 100).toFixed(1)}%`;

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-display text-sand">Motif trends</h3>
        <Badge label="Rolling 7/30 games" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-sand/60">
            <tr>
              <th className="text-left py-2">Motif</th>
              <th className="text-left">7g found</th>
              <th className="text-left">30g found</th>
              <th className="text-left">Last update</th>
            </tr>
          </thead>
          <tbody className="text-sand/90">
            {latestByMotif.map((row) => {
              const lastDate =
                row.seven?.trend_date || row.thirty?.trend_date || '--';
              return (
                <tr
                  key={row.motif}
                  className="odd:bg-white/0 even:bg-white/5/5 border-b border-white/5"
                >
                  <td className="py-2 font-display text-sm uppercase tracking-wide">
                    {row.motif}
                  </td>
                  <td className="font-mono text-xs text-teal">
                    {formatPercent(row.seven?.found_rate ?? null)}
                  </td>
                  <td className="font-mono text-xs text-teal">
                    {formatPercent(row.thirty?.found_rate ?? null)}
                  </td>
                  <td className="font-mono text-xs text-sand/70">{lastDate}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
