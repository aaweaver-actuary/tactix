import { API_BASE } from '../api';

export default function getJobStreamUrl(
  job: string,
  source?: string,
  profile?: string,
  backfillStartMs?: number,
  backfillEndMs?: number,
): string {
  const base = API_BASE ? API_BASE.replace(/\/$/, '') : '';
  const params = new URLSearchParams({ job });
  if (source) params.set('source', source);
  if (profile) params.set('profile', profile);
  if (typeof backfillStartMs === 'number') {
    params.set('backfill_start_ms', String(backfillStartMs));
  }
  if (typeof backfillEndMs === 'number') {
    params.set('backfill_end_ms', String(backfillEndMs));
  }
  return `${base}/api/jobs/stream?${params.toString()}`;
}
