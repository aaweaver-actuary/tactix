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
};

export type PieceColor = 'w' | 'b';
export type PieceType = 'p' | 'n' | 'b' | 'r' | 'q' | 'k';
export type ChessPlatform = 'lichess' | 'chesscom';
export type LichessProfile = 'rapid' | 'blitz' | 'bullet' | 'classical';
export type TextMode = 'normal' | 'uppercase' | 'teal' | 'error' | 'monospace';
export type TextSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl';
