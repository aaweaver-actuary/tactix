import { ChessPlatform } from '../types';

export const SOURCE_OPTIONS: {
  id: ChessPlatform;
  label: string;
  note: string;
}[] = [
  { id: 'all', label: 'All sites', note: 'Combined view' },
  { id: 'lichess', label: 'Lichess · Rapid', note: 'Perf: rapid' },
  { id: 'chesscom', label: 'Chess.com · Blitz', note: 'Time class: blitz' },
];
