import { describe, it, expect, vi, beforeEach } from 'vitest';
import triggerDashboardJob from './triggerDashboardJob';

const postMock = vi.hoisted(() => vi.fn());
const fetchDashboardMock = vi.hoisted(() => vi.fn());

vi.mock('../api', () => ({
  client: { post: postMock },
}));

vi.mock('./fetchDashboard', () => ({
  default: fetchDashboardMock,
}));

describe('triggerDashboardJob', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('posts the job and returns dashboard with filters', async () => {
    postMock.mockResolvedValueOnce(undefined);
    fetchDashboardMock.mockResolvedValueOnce({ ok: true });

    const result = await triggerDashboardJob(
      '/api/jobs/refresh_metrics',
      { source: 'alpha' },
      'alpha',
      { region: 'us' } as any,
    );

    expect(postMock).toHaveBeenCalledWith('/api/jobs/refresh_metrics', null, {
      params: { source: 'alpha' },
    });
    expect(fetchDashboardMock).toHaveBeenCalledWith('alpha', { region: 'us' });
    expect(result).toEqual({ ok: true });
  });

  it('supports jobs without filters', async () => {
    postMock.mockResolvedValueOnce(undefined);
    fetchDashboardMock.mockResolvedValueOnce({ ok: true });

    const result = await triggerDashboardJob(
      '/api/jobs/daily_game_sync',
      { source: undefined, backfill_start_ms: 1, backfill_end_ms: 2 },
      undefined,
    );

    expect(postMock).toHaveBeenCalledWith('/api/jobs/daily_game_sync', null, {
      params: { source: undefined, backfill_start_ms: 1, backfill_end_ms: 2 },
    });
    expect(fetchDashboardMock).toHaveBeenCalledWith(undefined, {});
    expect(result).toEqual({ ok: true });
  });
});
