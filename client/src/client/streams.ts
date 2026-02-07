import { API_BASE, DashboardFilters, authHeaders } from '../api';

export function getAuthHeaders(): Record<string, string> {
  return authHeaders;
}

export function getJobStreamUrl(
  job: string,
  source?: string,
  profile?: string,
  backfillStartMs?: number,
  backfillEndMs?: number,
): string {
  const base = API_BASE ? API_BASE.replace(/\/$/, '') : '';
  const params = new URLSearchParams();
  params.set('job', job);
  if (source && source !== 'all') params.set('source', source);
  if (profile) params.set('profile', profile);
  if (typeof backfillStartMs === 'number') {
    params.set('backfill_start_ms', String(backfillStartMs));
  }
  if (typeof backfillEndMs === 'number') {
    params.set('backfill_end_ms', String(backfillEndMs));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : '';
  return `${base}/api/jobs/stream${suffix}`;
}

export function getMetricsStreamUrl(
  source?: string,
  filters: DashboardFilters = {},
): string {
  const base = API_BASE ? API_BASE.replace(/\/$/, '') : '';
  const params = new URLSearchParams();
  if (source && source !== 'all') {
    params.set('source', source);
  }
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === '') return;
    params.set(key, String(value));
  });
  const query = params.toString();
  const suffix = query ? `?${query}` : '';
  return `${base}/api/metrics/stream${suffix}`;
}

export async function openEventStream(
  streamUrl: string,
  signal: AbortSignal,
): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const response = await fetch(streamUrl, {
    headers: getAuthHeaders(),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`Stream failed with status ${response.status}`);
  }
  return response.body.getReader();
}
