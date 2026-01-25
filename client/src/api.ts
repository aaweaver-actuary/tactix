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

export type DashboardFilters = {
  motif?: string;
  rating_bucket?: string;
  time_control?: string;
  start_date?: string;
  end_date?: string;
};

export type PracticeQueueItem = {
  tactic_id: number;
  game_id: string;
  position_id: number;
  source: string;
  motif: string;
  result: string;
  best_uci: string;
  user_uci: string;
  eval_delta: number;
  severity: number;
  created_at: string;
  fen: string;
  position_uci: string;
  san: string;
  ply: number;
  move_number: number;
  side_to_move: string | null;
  clock_seconds: number | null;
};

export type PracticeQueueResponse = {
  source: string;
  include_failed_attempt: boolean;
  items: PracticeQueueItem[];
};

export type PracticeAttemptRequest = {
  tactic_id: number;
  position_id: number;
  attempted_uci: string;
  source?: string;
};

export type PracticeAttemptResponse = {
  attempt_id: number;
  tactic_id: number;
  position_id: number;
  source: string | null;
  attempted_uci: string;
  best_uci: string;
  best_san?: string | null;
  correct: boolean;
  motif: string;
  severity: number;
  eval_delta: number;
  message: string;
  explanation?: string | null;
};

const API_BASE = (import.meta.env.VITE_API_BASE || '').trim();
const API_TOKEN = (
  import.meta.env.VITE_TACTIX_API_TOKEN || 'local-dev-token'
).trim();
const authHeaders: Record<string, string> = API_TOKEN
  ? { Authorization: `Bearer ${API_TOKEN}` }
  : {};

const client = axios.create({
  baseURL: API_BASE || undefined,
  headers: authHeaders,
});

export function getAuthHeaders(): Record<string, string> {
  return authHeaders;
}

export function getJobStreamUrl(job: string, source?: string): string {
  const base = API_BASE ? API_BASE.replace(/\/$/, '') : '';
  const params = new URLSearchParams({ job });
  if (source) params.set('source', source);
  return `${base}/api/jobs/stream?${params.toString()}`;
}

export async function fetchDashboard(
  source?: string,
  filters: DashboardFilters = {},
): Promise<DashboardPayload> {
  const params = Object.fromEntries(
    Object.entries({ t: Date.now(), source, ...filters }).filter(
      ([, value]) => value !== undefined && value !== '',
    ),
  );
  const res = await client.get<DashboardPayload>('/api/dashboard', {
    params,
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
  filters: DashboardFilters = {},
): Promise<DashboardPayload> {
  await client.post('/api/jobs/refresh_metrics', null, { params: { source } });
  return fetchDashboard(source, filters);
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

export async function fetchPracticeQueue(
  source?: string,
  includeFailedAttempt = false,
): Promise<PracticeQueueResponse> {
  const res = await client.get<PracticeQueueResponse>('/api/practice/queue', {
    params: {
      source,
      include_failed_attempt: includeFailedAttempt,
    },
  });
  return res.data;
}

export async function submitPracticeAttempt(
  payload: PracticeAttemptRequest,
): Promise<PracticeAttemptResponse> {
  const res = await client.post<PracticeAttemptResponse>(
    '/api/practice/attempt',
    payload,
  );
  return res.data;
}
