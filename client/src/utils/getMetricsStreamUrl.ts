import { API_BASE } from '../api';
import type { DashboardFilters } from '../api';

export default function getMetricsStreamUrl(
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
