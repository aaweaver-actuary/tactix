import { LichessProfile } from '../types';

export const LICHESS_PROFILE_OPTIONS: {
  id: LichessProfile;
  label: string;
  note: string;
}[] = [
  { id: 'rapid', label: 'Rapid', note: 'Perf: rapid' },
  { id: 'blitz', label: 'Blitz', note: 'Perf: blitz' },
  { id: 'bullet', label: 'Bullet', note: 'Perf: bullet' },
  { id: 'classical', label: 'Classical', note: 'Perf: classical' },
];

export const LICHESS_PROFILE_LABELS = LICHESS_PROFILE_OPTIONS.reduce(
  (acc, option) => {
    acc[option.id] = option.label;
    return acc;
  },
  {} as Record<LichessProfile, string>,
);
