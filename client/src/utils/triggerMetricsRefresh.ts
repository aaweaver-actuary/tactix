import { DashboardFilters, DashboardPayload, client } from '../api';
import fetchDashboard from '../utils/fetchDashboard';

export default async function triggerMetricsRefresh(
  source?: string,
  filters: DashboardFilters = {},
): Promise<DashboardPayload> {
  await client.post('/api/jobs/refresh_metrics', null, { params: { source } });
  return fetchDashboard(source, filters);
}
