import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { fetchDashboard, fetchGameDetail } from './dashboard';
import { client } from '../api';

vi.mock('../api', () => ({
  client: {
    get: vi.fn(),
  },
}));

describe('client/dashboard', () => {
  const getMock = client.get as unknown as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    getMock.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('fetches dashboard with filtered params', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(1234);
    const payload = { ok: true } as any;
    getMock.mockResolvedValue({ data: payload });

    const result = await fetchDashboard('lichess', {
      motif: 'fork',
      rating_bucket: '',
      time_control: undefined,
    } as any);

    expect(getMock).toHaveBeenCalledWith('/api/dashboard', {
      params: { t: 1234, source: 'lichess', motif: 'fork' },
    });
    expect(result).toBe(payload);
  });

  it('fetches game detail and omits empty source', async () => {
    const payload = { ok: true } as any;
    getMock.mockResolvedValue({ data: payload });

    await fetchGameDetail('game/1', '');

    expect(getMock).toHaveBeenCalledWith('/api/games/game%2F1', {
      params: {},
    });
  });

  it('fetches game detail and omits source when set to all', async () => {
    const payload = { ok: true } as any;
    getMock.mockResolvedValue({ data: payload });

    await fetchGameDetail('game/2', 'all');

    expect(getMock).toHaveBeenCalledWith('/api/games/game%2F2', {
      params: {},
    });
  });
});
