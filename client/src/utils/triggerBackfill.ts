import { DashboardPayload, client } from '../api';
import fetchDashboard from './fetchDashboard';

export async function triggerBackfill(
  source: string | undefined,
  windowStartMs: number,
  windowEndMs: number,
): Promise<DashboardPayload> {
  await client.post('/api/jobs/daily_game_sync', null, {
    params: {
      source,
      backfill_start_ms: windowStartMs,
      backfill_end_ms: windowEndMs,
    },
  });
  return fetchDashboard(source);
}
