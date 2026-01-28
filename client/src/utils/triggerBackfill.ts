import { DashboardPayload } from '../api';
import triggerDashboardJob from './triggerDashboardJob';

export async function triggerBackfill(
  source: string | undefined,
  windowStartMs: number,
  windowEndMs: number,
  profile?: string,
): Promise<DashboardPayload> {
  return triggerDashboardJob(
    '/api/jobs/daily_game_sync',
    {
      source,
      backfill_start_ms: windowStartMs,
      backfill_end_ms: windowEndMs,
      profile,
    },
    source,
  );
}
