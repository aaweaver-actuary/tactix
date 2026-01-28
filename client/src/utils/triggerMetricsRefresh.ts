import { DashboardFilters, DashboardPayload } from '../api';
import triggerDashboardJob from './triggerDashboardJob';

export default async function triggerMetricsRefresh(
  source?: string,
  filters: DashboardFilters = {},
): Promise<DashboardPayload> {
  return triggerDashboardJob(
    '/api/jobs/refresh_metrics',
    { source },
    source,
    filters,
  );
}
