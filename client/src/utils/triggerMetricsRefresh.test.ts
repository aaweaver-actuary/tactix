import { describe, it, expect, vi, beforeEach } from 'vitest';
import triggerMetricsRefresh from './triggerMetricsRefresh';
import { client } from '../api';
import fetchDashboard from '../utils/fetchDashboard';

vi.mock('../api', () => ({
  client: { post: vi.fn() },
}));

vi.mock('../utils/fetchDashboard', () => ({
  fetchDashboard: vi.fn(),
}));

describe('triggerMetricsRefresh', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts refresh and returns dashboard without source/filters', async () => {
    (client.post as any).mockResolvedValue(undefined);
    (fetchDashboard as any).mockResolvedValue({ ok: true });

    const result = await triggerMetricsRefresh();

    expect(client.post).toHaveBeenCalledWith(
      '/api/jobs/refresh_metrics',
      null,
      {
        params: { source: undefined },
      },
    );
    expect(fetchDashboard).toHaveBeenCalledWith(undefined, {});
    expect(result).toEqual({ ok: true });
  });

  it('passes source and filters through', async () => {
    (client.post as any).mockResolvedValue(undefined);
    (fetchDashboard as any).mockResolvedValue({ data: 'dash' });

    const result = await triggerMetricsRefresh('alpha', {
      region: 'us',
    } as any);

    expect(client.post).toHaveBeenCalledWith(
      '/api/jobs/refresh_metrics',
      null,
      {
        params: { source: 'alpha' },
      },
    );
    expect(fetchDashboard).toHaveBeenCalledWith('alpha', { region: 'us' });
    expect(result).toEqual({ data: 'dash' });
  });
});
