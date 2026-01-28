import { describe, it, expect, vi, beforeEach } from 'vitest';
import { triggerBackfill } from './triggerBackfill';

const triggerDashboardJobMock = vi.hoisted(() => vi.fn());

vi.mock('./triggerDashboardJob', () => ({
  default: triggerDashboardJobMock,
}));

describe('triggerBackfill', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('posts backfill job and returns dashboard for a source', async () => {
    const resultPayload = { ok: true } as any;
    triggerDashboardJobMock.mockResolvedValue(resultPayload);

    const result = await triggerBackfill('steam', 100, 200);

    expect(triggerDashboardJobMock).toHaveBeenCalledWith(
      '/api/jobs/daily_game_sync',
      {
        source: 'steam',
        backfill_start_ms: 100,
        backfill_end_ms: 200,
      },
      'steam',
    );
    expect(result).toBe(resultPayload);
  });

  it('handles undefined source', async () => {
    const resultPayload = { ok: true } as any;
    triggerDashboardJobMock.mockResolvedValue(resultPayload);

    const result = await triggerBackfill(undefined, 1, 2);

    expect(triggerDashboardJobMock).toHaveBeenCalledWith(
      '/api/jobs/daily_game_sync',
      {
        source: undefined,
        backfill_start_ms: 1,
        backfill_end_ms: 2,
      },
      undefined,
    );
    expect(result).toBe(resultPayload);
  });

  it('passes profile when provided', async () => {
    const resultPayload = { ok: true } as any;
    triggerDashboardJobMock.mockResolvedValue(resultPayload);

    const result = await triggerBackfill('lichess', 10, 20, 'bullet');

    expect(triggerDashboardJobMock).toHaveBeenCalledWith(
      '/api/jobs/daily_game_sync',
      {
        source: 'lichess',
        backfill_start_ms: 10,
        backfill_end_ms: 20,
        profile: 'bullet',
      },
      'lichess',
    );
    expect(result).toBe(resultPayload);
  });
});
