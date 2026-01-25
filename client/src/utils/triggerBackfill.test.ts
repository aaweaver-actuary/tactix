import { describe, it, expect, vi, beforeEach } from 'vitest';
import { triggerBackfill } from './triggerBackfill';

const postMock = vi.hoisted(() => vi.fn());
const fetchDashboardMock = vi.hoisted(() => vi.fn());

vi.mock('../api', () => ({
  client: {
    post: postMock,
  },
}));

vi.mock('./fetchDashboard', () => ({
  default: fetchDashboardMock,
}));

describe('triggerBackfill', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('posts backfill job and returns dashboard for a source', async () => {
    const resultPayload = { ok: true } as any;
    postMock.mockResolvedValue(undefined);
    fetchDashboardMock.mockResolvedValue(resultPayload);

    const result = await triggerBackfill('steam', 100, 200);

    expect(postMock).toHaveBeenCalledWith('/api/jobs/daily_game_sync', null, {
      params: {
        source: 'steam',
        backfill_start_ms: 100,
        backfill_end_ms: 200,
      },
    });
    expect(fetchDashboardMock).toHaveBeenCalledWith('steam');
    expect(result).toBe(resultPayload);
  });

  it('handles undefined source', async () => {
    const resultPayload = { ok: true } as any;
    postMock.mockResolvedValue(undefined);
    fetchDashboardMock.mockResolvedValue(resultPayload);

    const result = await triggerBackfill(undefined, 1, 2);

    expect(postMock).toHaveBeenCalledWith('/api/jobs/daily_game_sync', null, {
      params: {
        source: undefined,
        backfill_start_ms: 1,
        backfill_end_ms: 2,
      },
    });
    expect(fetchDashboardMock).toHaveBeenCalledWith(undefined);
    expect(result).toBe(resultPayload);
  });

  it('passes profile when provided', async () => {
    const resultPayload = { ok: true } as any;
    postMock.mockResolvedValue(undefined);
    fetchDashboardMock.mockResolvedValue(resultPayload);

    const result = await triggerBackfill('lichess', 10, 20, 'bullet');

    expect(postMock).toHaveBeenCalledWith('/api/jobs/daily_game_sync', null, {
      params: {
        source: 'lichess',
        backfill_start_ms: 10,
        backfill_end_ms: 20,
        profile: 'bullet',
      },
    });
    expect(fetchDashboardMock).toHaveBeenCalledWith('lichess');
    expect(result).toBe(resultPayload);
  });
});
