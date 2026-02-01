import { describe, it, expect, vi } from 'vitest';

const loadWithApiBase = async (apiBase: string | undefined) => {
  vi.resetModules();
  vi.doMock('../api', () => ({ API_BASE: apiBase }));
  const mod = await import('./getJobStreamUrl');
  return mod.default;
};

describe('getJobStreamUrl', () => {
  it('builds URL with API_BASE and job param', async () => {
    const getJobStreamUrl = await loadWithApiBase('https://example.com');
    expect(getJobStreamUrl('abc')).toBe(
      'https://example.com/api/jobs/stream?job=abc',
    );
  });

  it('trims trailing slash from API_BASE', async () => {
    const getJobStreamUrl = await loadWithApiBase('https://example.com/');
    expect(getJobStreamUrl('abc')).toBe(
      'https://example.com/api/jobs/stream?job=abc',
    );
  });

  it('omits base when API_BASE is empty', async () => {
    const getJobStreamUrl = await loadWithApiBase('');
    expect(getJobStreamUrl('abc')).toBe('/api/jobs/stream?job=abc');
  });

  it('adds source param when provided', async () => {
    const getJobStreamUrl = await loadWithApiBase('https://example.com');
    expect(getJobStreamUrl('abc', 'worker1')).toBe(
      'https://example.com/api/jobs/stream?job=abc&source=worker1',
    );
  });

  it('omits source param when set to all', async () => {
    const getJobStreamUrl = await loadWithApiBase('https://example.com');
    expect(getJobStreamUrl('abc', 'all')).toBe(
      'https://example.com/api/jobs/stream?job=abc',
    );
  });

  it('adds profile param when provided', async () => {
    const getJobStreamUrl = await loadWithApiBase('https://example.com');
    expect(getJobStreamUrl('abc', 'lichess', 'bullet')).toBe(
      'https://example.com/api/jobs/stream?job=abc&source=lichess&profile=bullet',
    );
  });

  it('adds backfill window params when provided', async () => {
    const getJobStreamUrl = await loadWithApiBase('https://example.com');
    expect(getJobStreamUrl('daily_game_sync', 'lichess', 'rapid', 10, 20)).toBe(
      'https://example.com/api/jobs/stream?job=daily_game_sync&source=lichess&profile=rapid&backfill_start_ms=10&backfill_end_ms=20',
    );
  });

  it('encodes query params', async () => {
    const getJobStreamUrl = await loadWithApiBase('https://example.com');
    expect(getJobStreamUrl('a b', 'x/y')).toBe(
      'https://example.com/api/jobs/stream?job=a+b&source=x%2Fy',
    );
  });
});
