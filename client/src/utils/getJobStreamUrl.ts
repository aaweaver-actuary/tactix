import { API_BASE } from '../api';

export default function getJobStreamUrl(job: string, source?: string): string {
  const base = API_BASE ? API_BASE.replace(/\/$/, '') : '';
  const params = new URLSearchParams({ job });
  if (source) params.set('source', source);
  return `${base}/api/jobs/stream?${params.toString()}`;
}
