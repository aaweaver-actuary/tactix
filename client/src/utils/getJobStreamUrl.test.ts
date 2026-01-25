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

  it('encodes query params', async () => {
    const getJobStreamUrl = await loadWithApiBase('https://example.com');
    expect(getJobStreamUrl('a b', 'x/y')).toBe(
      'https://example.com/api/jobs/stream?job=a+b&source=x%2Fy',
    );
  });
});
