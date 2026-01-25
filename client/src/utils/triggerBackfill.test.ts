import { describe, it, expect, vi, beforeEach } from 'vitest';
import { triggerBackfill } from './triggerBackfill';
import { client } from '../api';
import fetchDashboard from './fetchDashboard';

vi.mock('../api', () => ({
  client: {
    post: vi.fn(),
  },
}));

vi.mock('./fetchDashboard', () => ({
  fetchDashboard: vi.fn(),
}));

describe('triggerBackfill', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('posts backfill job and returns dashboard for a source', async () => {
    const resultPayload = { ok: true } as any;
    (client.post as any).mockResolvedValue(undefined);
    (fetchDashboard as any).mockResolvedValue(resultPayload);

    const result = await triggerBackfill('steam', 100, 200);

    expect(client.post).toHaveBeenCalledWith(
      '/api/jobs/daily_game_sync',
      null,
      {
        params: {
          source: 'steam',
          backfill_start_ms: 100,
          backfill_end_ms: 200,
        },
      },
    );
    expect(fetchDashboard).toHaveBeenCalledWith('steam');
    expect(result).toBe(resultPayload);
  });

  it('handles undefined source', async () => {
    const resultPayload = { ok: true } as any;
    (client.post as any).mockResolvedValue(undefined);
    (fetchDashboard as any).mockResolvedValue(resultPayload);

    const result = await triggerBackfill(undefined, 1, 2);

    expect(client.post).toHaveBeenCalledWith(
      '/api/jobs/daily_game_sync',
      null,
      {
        params: {
          source: undefined,
          backfill_start_ms: 1,
          backfill_end_ms: 2,
        },
      },
    );
    expect(fetchDashboard).toHaveBeenCalledWith(undefined);
    expect(result).toBe(resultPayload);
  });
});
