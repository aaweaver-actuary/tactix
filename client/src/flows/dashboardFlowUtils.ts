import type { ChessPlatform } from '../api';

export const DAY_MS = 24 * 60 * 60 * 1000;
export const BACKFILL_WINDOW_DAYS = 900;

const parseBackfillDate = (value: string, fallbackMs: number) => {
  const date = value ? new Date(`${value}T00:00:00`) : new Date(fallbackMs);
  return date.getTime();
};

export const resolveBackfillWindow = (
  startDate: string,
  endDate: string,
  nowMs: number,
) => {
  const startMs = parseBackfillDate(
    startDate,
    nowMs - BACKFILL_WINDOW_DAYS * DAY_MS,
  );
  const endMs = parseBackfillDate(endDate, nowMs);
  const cappedEnd = Math.min(endMs + DAY_MS, nowMs);
  if (Number.isNaN(startMs) || Number.isNaN(cappedEnd)) {
    throw new Error('Invalid backfill date range');
  }
  if (startMs >= cappedEnd) {
    throw new Error('Backfill range must end after the start date');
  }
  return { startMs, endMs: cappedEnd };
};

export const ensureSourceSelected = (
  source: ChessPlatform,
  setError: (message: string) => void,
  message: string,
) => {
  if (source !== 'all') return true;
  setError(message);
  return false;
};
