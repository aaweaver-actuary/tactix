import { describe, it, expect, vi, beforeEach } from 'vitest';
import triggerMetricsRefresh from './triggerMetricsRefresh';

const triggerDashboardJobMock = vi.hoisted(() => vi.fn());

vi.mock('./triggerDashboardJob', () => ({
  default: triggerDashboardJobMock,
}));

describe('triggerMetricsRefresh', () => {
  beforeEach(() => {
    triggerDashboardJobMock.mockReset();
  });

  it('posts refresh and returns dashboard without source/filters', async () => {
    triggerDashboardJobMock.mockResolvedValue({ ok: true });

    const result = await triggerMetricsRefresh();

    expect(triggerDashboardJobMock).toHaveBeenCalledWith(
      '/api/jobs/refresh_metrics',
      { source: undefined },
      undefined,
      {},
    );
    expect(result).toEqual({ ok: true });
  });

  it('passes source and filters through', async () => {
    triggerDashboardJobMock.mockResolvedValue({ data: 'dash' });

    const result = await triggerMetricsRefresh('alpha', {
      region: 'us',
    } as any);

    expect(triggerDashboardJobMock).toHaveBeenCalledWith(
      '/api/jobs/refresh_metrics',
      { source: 'alpha' },
      'alpha',
      { region: 'us' },
    );
    expect(result).toEqual({ data: 'dash' });
  });
});
