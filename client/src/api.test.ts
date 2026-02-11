import { describe, expect, it, vi } from 'vitest';

describe('api env setup', () => {
  it('builds auth headers when token is present', async () => {
    vi.resetModules();
    vi.stubEnv('VITE_API_BASE', 'https://api.test');
    vi.stubEnv('VITE_TACTIX_API_TOKEN', 'test-token');

    const mod = await import('./api');
    expect(mod.authHeaders).toEqual({ Authorization: 'Bearer test-token' });
    expect(mod.client.defaults.baseURL).toBe('https://api.test');
  });

  it('omits auth headers when token is blank', async () => {
    vi.resetModules();
    vi.stubEnv('VITE_API_BASE', '');
    vi.stubEnv('VITE_TACTIX_API_TOKEN', '   ');

    const mod = await import('./api');
    expect(mod.authHeaders).toEqual({});
  });
});
