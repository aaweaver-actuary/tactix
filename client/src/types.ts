export type JobProgressItem = {
  step: string;
  timestamp?: number;
  message?: string;
  analyzed?: number;
  total?: number;
  fetched_games?: number;
  positions?: number;
  metrics_version?: number;
  schema_version?: number;
  job?: string;
  job_id?: string;
};

export type ChessPlatform = 'lichess' | 'chesscom' | 'all';
export type LichessProfile =
  | 'rapid'
  | 'blitz'
  | 'bullet'
  | 'classical'
  | 'correspondence';
export type ChesscomProfile =
  | 'blitz'
  | 'bullet'
  | 'rapid'
  | 'classical'
  | 'correspondence';
export type TextMode = 'normal' | 'uppercase' | 'teal' | 'error' | 'monospace';
export type TextSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl';
