import { DashboardPayload, client } from '../api';
import fetchDashboard from '../utils/fetchDashboard';

export default async function triggerPipeline(
  source?: string,
): Promise<DashboardPayload> {
  await client.post('/api/jobs/daily_game_sync', null, { params: { source } });
  return fetchDashboard(source);
}
