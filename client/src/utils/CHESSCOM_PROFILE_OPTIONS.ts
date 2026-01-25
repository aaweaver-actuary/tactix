import { ChesscomProfile } from '../types';

export const CHESSCOM_PROFILE_OPTIONS: {
  id: ChesscomProfile;
  label: string;
  note: string;
}[] = [
  { id: 'blitz', label: 'Blitz', note: 'Time class: blitz' },
  { id: 'bullet', label: 'Bullet', note: 'Time class: bullet' },
  { id: 'rapid', label: 'Rapid', note: 'Time class: rapid' },
  { id: 'classical', label: 'Classical', note: 'Time class: classical' },
  { id: 'correspondence', label: 'Correspondence', note: 'Time class: daily' },
];

export const CHESSCOM_PROFILE_LABELS = CHESSCOM_PROFILE_OPTIONS.reduce(
  (acc, option) => {
    acc[option.id] = option.label;
    return acc;
  },
  {} as Record<ChesscomProfile, string>,
);
