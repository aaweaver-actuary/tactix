import axios from 'axios';

export type MetricsRow = {
  motif: string;
  total: number;
  found: number;
  missed: number;
  failed_attempt: number;
  unclear: number;
  updated_at: string;
};

export type TacticRow = {
  tactic_id: number;
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
  game_id: string;
  fen: string;
  san: string;
  uci: string;
  move_number: number;
  clock_seconds: number | null;
  created_at: string;
};

export type DashboardPayload = {
  metrics: MetricsRow[];
  positions: PositionRow[];
  tactics: TacticRow[];
  metrics_version: number;
};

const client = axios.create({
  baseURL: '',
});

export async function fetchDashboard(): Promise<DashboardPayload> {
  const res = await client.get<DashboardPayload>('/api/dashboard', {
    params: { t: Date.now() },
  });
  return res.data;
}

export async function triggerPipeline(): Promise<DashboardPayload> {
  await client.post('/api/jobs/daily_game_sync');
  return fetchDashboard();
}
