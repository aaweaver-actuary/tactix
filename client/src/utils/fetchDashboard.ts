import { DashboardFilters, DashboardPayload, client } from '../api';

export default async function fetchDashboard(
  source?: string,
  filters: DashboardFilters = {},
): Promise<DashboardPayload> {
  const params = Object.fromEntries(
    Object.entries({
      t: Date.now(),
      source: source === 'all' ? undefined : source,
      ...filters,
    }).filter(([, value]) => value !== undefined && value !== ''),
  );
  const res = await client.get<DashboardPayload>('/api/dashboard', {
    params,
  });
  return res.data;
}
