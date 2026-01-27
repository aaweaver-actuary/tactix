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
  served_at_ms?: number;
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
  success?: boolean;
  motif: string;
  severity: number;
  eval_delta: number;
  message: string;
  explanation?: string | null;
  latency_ms?: number | null;
};

export type PostgresOpsEvent = {
  id: number;
  component: string;
  event_type: string;
  source: string | null;
  profile: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
};

export type PostgresStatus = {
  enabled: boolean;
  status: 'ok' | 'disabled' | 'unreachable';
  latency_ms?: number;
  error?: string;
  schema?: string;
  tables?: string[];
  events?: PostgresOpsEvent[];
};

export type PostgresAnalysisRow = {
  tactic_id: number;
  game_id: string | null;
  position_id: number;
  motif: string | null;
  severity: number | null;
  best_uci: string | null;
  best_san: string | null;
  explanation: string | null;
  eval_cp: number | null;
  created_at: string;
  result: string | null;
  user_uci: string | null;
  eval_delta: number | null;
  outcome_created_at: string | null;
};

export type PostgresAnalysisResponse = {
  status: string;
  tactics: PostgresAnalysisRow[];
};

export type PostgresRawPgnSourceSummary = {
  source: string;
  total_rows: number;
  distinct_games: number;
  latest_ingested_at: string | null;
};

export type PostgresRawPgnsSummary = {
  status: string;
  total_rows: number;
  distinct_games: number;
  latest_ingested_at: string | null;
  sources: PostgresRawPgnSourceSummary[];
};

export const API_BASE = (import.meta.env.VITE_API_BASE || '').trim();
const API_TOKEN = (
  import.meta.env.VITE_TACTIX_API_TOKEN || 'local-dev-token'
).trim();
export const authHeaders: Record<string, string> = API_TOKEN
  ? { Authorization: `Bearer ${API_TOKEN}` }
  : {};

export const client = axios.create({
  baseURL: API_BASE || undefined,
  headers: authHeaders,
});
