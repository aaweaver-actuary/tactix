import { DashboardFilters, DashboardPayload, client } from '../api';
import fetchDashboard from './fetchDashboard';

type JobParams = Record<string, unknown>;

/**
 * Posts a dashboard-related job and then fetches the refreshed dashboard payload.
 */
export default async function triggerDashboardJob(
  jobPath: string,
  params: JobParams,
  source?: string,
  filters: DashboardFilters = {},
): Promise<DashboardPayload> {
  await client.post(jobPath, null, { params });
  return fetchDashboard(source, filters);
}
