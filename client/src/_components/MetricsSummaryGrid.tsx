import BaseMetricsCards from './BaseMetricsCards';
import SourceSyncCards from './SourceSyncCards';
import { DashboardPayload } from '../api';

interface MetricsSummaryGridProps {
  positions: number;
  tactics: number;
  metricsVersion: number;
  sourceSync?: DashboardPayload['source_sync'];
}

export default function MetricsSummaryGrid({
  positions,
  tactics,
  metricsVersion,
  sourceSync,
}: MetricsSummaryGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <BaseMetricsCards
        positions={positions}
        tactics={tactics}
        metricsVersion={metricsVersion}
      />
      <SourceSyncCards sourceSync={sourceSync} />
    </div>
  );
}
