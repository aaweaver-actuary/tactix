import { describe, expect, it, vi } from 'vitest';

vi.mock('../utils/fetchPostgresResource', () => ({
  fetchPostgresResource: vi.fn(),
}));

const { fetchPostgresStatus, fetchPostgresAnalysis, fetchPostgresRawPgns } =
  await import('./postgres');
const { fetchPostgresResource } =
  await import('../utils/fetchPostgresResource');

describe('postgres client helpers', () => {
  it('calls the status endpoint', async () => {
    (
      fetchPostgresResource as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValueOnce({});

    await fetchPostgresStatus();

    expect(fetchPostgresResource).toHaveBeenCalledWith('status', 'status');
  });

  it('calls the analysis endpoint', async () => {
    (
      fetchPostgresResource as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValueOnce({});

    await fetchPostgresAnalysis();

    expect(fetchPostgresResource).toHaveBeenCalledWith('analysis', 'analysis');
  });

  it('calls the raw PGNs endpoint', async () => {
    (
      fetchPostgresResource as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValueOnce({});

    await fetchPostgresRawPgns();

    expect(fetchPostgresResource).toHaveBeenCalledWith('raw_pgns', 'raw PGNs');
  });
});
