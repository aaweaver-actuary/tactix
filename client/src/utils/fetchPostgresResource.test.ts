import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchPostgresResource } from './fetchPostgresResource';

const fetchMock = vi.fn();

vi.mock('../api', () => ({
  API_BASE: 'http://api.test',
}));

vi.mock('./getAuthHeaders', () => ({
  getAuthHeaders: () => ({ Authorization: 'Bearer test' }),
}));

describe('fetchPostgresResource', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('fetches a resource with auth headers and returns JSON', async () => {
    const payload = { ok: true };
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue(payload),
    });

    const result = await fetchPostgresResource<typeof payload>(
      'analysis',
      'analysis',
    );

    expect(fetchMock).toHaveBeenCalledWith(
      'http://api.test/api/postgres/analysis',
      {
        headers: { Authorization: 'Bearer test' },
      },
    );
    expect(result).toEqual(payload);
  });

  it('throws with the expected error message when the response is not ok', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 503,
      json: vi.fn(),
    });

    await expect(fetchPostgresResource('status', 'status')).rejects.toThrow(
      'Postgres status fetch failed: 503',
    );
  });
});
