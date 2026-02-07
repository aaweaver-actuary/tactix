import { DashboardFilters, DashboardPayload, client } from '../api';
import { fetchDashboard } from './dashboard';

type JobParams = Record<string, unknown>;

export async function triggerDashboardJob(
  jobPath: string,
  params: JobParams,
  source?: string,
  filters: DashboardFilters = {},
): Promise<DashboardPayload> {
  await client.post(jobPath, null, { params });
  return fetchDashboard(source, filters);
}

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

export async function triggerMetricsRefresh(
  source?: string,
  filters: DashboardFilters = {},
): Promise<DashboardPayload> {
  return triggerDashboardJob(
    '/api/jobs/refresh_metrics',
    { source: source === 'all' ? undefined : source },
    source === 'all' ? undefined : source,
    filters,
  );
}

export async function triggerPipeline(
  source?: string,
): Promise<DashboardPayload> {
  return triggerDashboardJob('/api/jobs/daily_game_sync', { source }, source);
}

export async function triggerMigrations(source?: string): Promise<{
  status: string;
  result: { source: string; schema_version: number };
}> {
  const res = await client.post('/api/jobs/migrations', null, {
    params: { source },
  });
  return res.data;
}
