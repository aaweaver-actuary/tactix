import { describe, it, expect, vi, beforeEach } from 'vitest';
import triggerPipeline from './triggerPipeline';

const postMock = vi.fn();

vi.mock('../api', () => ({
  client: { post: postMock },
}));

const fetchDashboardMock = vi.fn();

vi.mock('../utils/fetchDashboard', () => ({
  fetchDashboard: fetchDashboardMock,
}));

describe('triggerPipeline', () => {
  beforeEach(() => {
    postMock.mockReset();
    fetchDashboardMock.mockReset();
  });

  it('posts the job and returns the dashboard with a source', async () => {
    const source = 'test-source';
    postMock.mockResolvedValueOnce(undefined);
    const dashboard = { ok: true };
    fetchDashboardMock.mockResolvedValueOnce(dashboard);

    const result = await triggerPipeline(source);

    expect(postMock).toHaveBeenCalledWith('/api/jobs/daily_game_sync', null, {
      params: { source },
    });
    expect(fetchDashboardMock).toHaveBeenCalledWith(source);
    expect(result).toBe(dashboard);
  });

  it('posts the job and returns the dashboard without a source', async () => {
    postMock.mockResolvedValueOnce(undefined);
    const dashboard = { ok: true };
    fetchDashboardMock.mockResolvedValueOnce(dashboard);

    const result = await triggerPipeline();

    expect(postMock).toHaveBeenCalledWith('/api/jobs/daily_game_sync', null, {
      params: { source: undefined },
    });
    expect(fetchDashboardMock).toHaveBeenCalledWith(undefined);
    expect(result).toBe(dashboard);
  });
});
