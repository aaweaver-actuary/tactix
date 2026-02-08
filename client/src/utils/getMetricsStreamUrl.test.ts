import { describe, it, expect, vi } from 'vitest';

const loadWithApiBase = async (apiBase: string | undefined) => {
  vi.resetModules();
  vi.doMock('../api', () => ({ API_BASE: apiBase }));
  const mod = await import('./getMetricsStreamUrl');
  return mod.default;
};

describe('getMetricsStreamUrl', () => {
  it('builds URL with API_BASE', async () => {
    const getMetricsStreamUrl = await loadWithApiBase('https://example.com');
    expect(getMetricsStreamUrl('lichess')).toBe(
      'https://example.com/api/metrics/stream?source=lichess',
    );
  });

  it('trims trailing slash from API_BASE', async () => {
    const getMetricsStreamUrl = await loadWithApiBase('https://example.com/');
    expect(getMetricsStreamUrl('lichess')).toBe(
      'https://example.com/api/metrics/stream?source=lichess',
    );
  });

  it('omits base when API_BASE is empty', async () => {
    const getMetricsStreamUrl = await loadWithApiBase('');
    expect(getMetricsStreamUrl('lichess')).toBe(
      '/api/metrics/stream?source=lichess',
    );
  });

  it('omits source param when set to all', async () => {
    const getMetricsStreamUrl = await loadWithApiBase('https://example.com');
    expect(getMetricsStreamUrl('all')).toBe(
      'https://example.com/api/metrics/stream',
    );
  });

  it('adds filter params when provided', async () => {
    const getMetricsStreamUrl = await loadWithApiBase('https://example.com');
    expect(
      getMetricsStreamUrl('lichess', {
        motif: 'fork',
        rating_bucket: '1200',
        time_control: 'blitz',
        start_date: '2024-01-01',
        end_date: '2024-02-01',
      }),
    ).toBe(
      'https://example.com/api/metrics/stream?source=lichess&motif=fork&rating_bucket=1200&time_control=blitz&start_date=2024-01-01&end_date=2024-02-01',
    );
  });

  it('encodes query params', async () => {
    const getMetricsStreamUrl = await loadWithApiBase('https://example.com');
    expect(getMetricsStreamUrl('chesscom', { motif: 'mate in 1' })).toBe(
      'https://example.com/api/metrics/stream?source=chesscom&motif=mate+in+1',
    );
  });
});
