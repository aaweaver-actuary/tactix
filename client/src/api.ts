import axios from 'axios';

export type MetricsRow = {
  source: string;
  metric_type: string;
  motif: string;
  window_days: number | null;
  trend_date: string | null;
  rating_bucket: string | null;
  time_control: string | null;
  total: number;
  found: number;
  missed: number;
  failed_attempt: number;
  unclear: number;
  found_rate: number | null;
  miss_rate: number | null;
  updated_at: string;
};

export type TacticRow = {
  tactic_id: number;
  source: string | null;
  motif: string;
  result: string;
  user_uci: string;
  eval_delta: number;
  severity: number;
  created_at: string;
  best_uci: string;
};

export type PositionRow = {
  position_id: number;
  source: string;
  game_id: string;
  fen: string;
  san: string;
  uci: string;
  move_number: number;
  clock_seconds: number | null;
  created_at: string;
};

export type DashboardPayload = {
  source: string;
  user: string;
  metrics: MetricsRow[];
  positions: PositionRow[];
  tactics: TacticRow[];
  metrics_version: number;
};

const API_BASE = (import.meta.env.VITE_API_BASE || '').trim();

const client = axios.create({
  baseURL: API_BASE || undefined,
});

export function getJobStreamUrl(job: string, source?: string): string {
  const base = API_BASE ? API_BASE.replace(/\/$/, '') : '';
  const params = new URLSearchParams({ job });
  if (source) params.set('source', source);
  return `${base}/api/jobs/stream?${params.toString()}`;
}

export async function fetchDashboard(
  source?: string,
): Promise<DashboardPayload> {
  const res = await client.get<DashboardPayload>('/api/dashboard', {
    params: { t: Date.now(), source },
  });
  return res.data;
}

export async function triggerPipeline(
  source?: string,
): Promise<DashboardPayload> {
  await client.post('/api/jobs/daily_game_sync', null, { params: { source } });
  return fetchDashboard(source);
}

export async function triggerMetricsRefresh(
  source?: string,
): Promise<DashboardPayload> {
  await client.post('/api/jobs/refresh_metrics', null, { params: { source } });
  return fetchDashboard(source);
}
