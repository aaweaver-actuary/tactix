import { describe, it, expect, vi, beforeEach } from 'vitest';
import triggerMetricsRefresh from './triggerMetricsRefresh';

const postMock = vi.hoisted(() => vi.fn());
const fetchDashboardMock = vi.hoisted(() => vi.fn());

vi.mock('../api', () => ({
  client: { post: postMock },
}));

vi.mock('../utils/fetchDashboard', () => ({
  default: fetchDashboardMock,
}));

describe('triggerMetricsRefresh', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts refresh and returns dashboard without source/filters', async () => {
    postMock.mockResolvedValue(undefined);
    fetchDashboardMock.mockResolvedValue({ ok: true });

    const result = await triggerMetricsRefresh();

    expect(postMock).toHaveBeenCalledWith('/api/jobs/refresh_metrics', null, {
      params: { source: undefined },
    });
    expect(fetchDashboardMock).toHaveBeenCalledWith(undefined, {});
    expect(result).toEqual({ ok: true });
  });

  it('passes source and filters through', async () => {
    postMock.mockResolvedValue(undefined);
    fetchDashboardMock.mockResolvedValue({ data: 'dash' });

    const result = await triggerMetricsRefresh('alpha', {
      region: 'us',
    } as any);

    expect(postMock).toHaveBeenCalledWith('/api/jobs/refresh_metrics', null, {
      params: { source: 'alpha' },
    });
    expect(fetchDashboardMock).toHaveBeenCalledWith('alpha', { region: 'us' });
    expect(result).toEqual({ data: 'dash' });
  });
});
