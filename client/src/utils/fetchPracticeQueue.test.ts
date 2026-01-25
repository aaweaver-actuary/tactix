import { describe, it, expect, vi, beforeEach } from 'vitest';
import fetchPracticeQueue from './fetchPracticeQueue';

const getMock = vi.hoisted(() => vi.fn());

vi.mock('../api', () => ({
  client: {
    get: getMock,
  },
}));

describe('fetchPracticeQueue', () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it('calls client.get with default params and returns data', async () => {
    const data = { items: [], total: 0 };
    getMock.mockResolvedValue({ data });

    const result = await fetchPracticeQueue();

    expect(getMock).toHaveBeenCalledWith('/api/practice/queue', {
      params: {
        source: undefined,
        include_failed_attempt: false,
      },
    });
    expect(result).toBe(data);
  });

  it('passes source and includeFailedAttempt', async () => {
    const data = { items: [{ id: '1' }], total: 1 };
    getMock.mockResolvedValue({ data });

    const result = await fetchPracticeQueue('deck', true);

    expect(getMock).toHaveBeenCalledWith('/api/practice/queue', {
      params: {
        source: 'deck',
        include_failed_attempt: true,
      },
    });
    expect(result).toBe(data);
  });
});
