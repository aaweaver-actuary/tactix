import { describe, it, expect, vi, beforeEach } from 'vitest';
import triggerPipeline from './triggerPipeline';

const triggerDashboardJobMock = vi.hoisted(() => vi.fn());

vi.mock('./triggerDashboardJob', () => ({
  default: triggerDashboardJobMock,
}));

describe('triggerPipeline', () => {
  beforeEach(() => {
    triggerDashboardJobMock.mockReset();
  });

  it('posts the job and returns the dashboard with a source', async () => {
    const source = 'test-source';
    const dashboard = { ok: true };
    triggerDashboardJobMock.mockResolvedValueOnce(dashboard);

    const result = await triggerPipeline(source);

    expect(triggerDashboardJobMock).toHaveBeenCalledWith(
      '/api/jobs/daily_game_sync',
      { source },
      source,
    );
    expect(result).toBe(dashboard);
  });

  it('posts the job and returns the dashboard without a source', async () => {
    const dashboard = { ok: true };
    triggerDashboardJobMock.mockResolvedValueOnce(dashboard);

    const result = await triggerPipeline();

    expect(triggerDashboardJobMock).toHaveBeenCalledWith(
      '/api/jobs/daily_game_sync',
      { source: undefined },
      undefined,
    );
    expect(result).toBe(dashboard);
  });
});
