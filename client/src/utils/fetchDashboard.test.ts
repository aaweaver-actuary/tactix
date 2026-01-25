import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fetchDashboard from './fetchDashboard';
import { client } from '../api';

vi.mock('../api', () => ({
  client: {
    get: vi.fn(),
  },
}));

describe('fetchDashboard', () => {
  const getMock = client.get as unknown as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    getMock.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('calls client.get with filtered params and returns data', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(123456789);
    const payload = { ok: true } as unknown as any;
    getMock.mockResolvedValue({ data: payload });

    const result = await fetchDashboard('src', {
      a: 'x',
      b: '',
      c: undefined,
    } as any);

    expect(getMock).toHaveBeenCalledWith('/api/dashboard', {
      params: { t: 123456789, source: 'src', a: 'x' },
    });
    expect(result).toBe(payload);
  });

  it('omits source when undefined', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(42);
    const payload = { ok: true } as unknown as any;
    getMock.mockResolvedValue({ data: payload });

    await fetchDashboard(undefined, { foo: 'bar' } as any);

    expect(getMock).toHaveBeenCalledWith('/api/dashboard', {
      params: { t: 42, foo: 'bar' },
    });
  });

  it('handles empty filters', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(7);
    const payload = { ok: true } as unknown as any;
    getMock.mockResolvedValue({ data: payload });

    const result = await fetchDashboard();

    expect(getMock).toHaveBeenCalledWith('/api/dashboard', {
      params: { t: 7 },
    });
    expect(result).toBe(payload);
  });
});
