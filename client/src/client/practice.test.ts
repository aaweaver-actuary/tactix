import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { client } from '../api';

vi.mock('../api', () => ({
  client: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('client/practice', () => {
  const getMock = client.get as unknown as ReturnType<typeof vi.fn>;
  const postMock = client.post as unknown as ReturnType<typeof vi.fn>;
  const loadPractice = async () => import('./practice');

  beforeEach(() => {
    vi.resetModules();
    getMock.mockReset();
    postMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('includes a valid practice queue limit in params', async () => {
    vi.stubEnv('VITE_PRACTICE_QUEUE_LIMIT', '5');
    const payload = { ok: true } as any;
    getMock.mockResolvedValue({ data: payload });

    const { fetchPracticeQueue } = await loadPractice();
    const result = await fetchPracticeQueue('lichess', true);

    expect(getMock).toHaveBeenCalledWith('/api/practice/queue', {
      params: {
        source: 'lichess',
        include_failed_attempt: true,
        limit: 5,
      },
    });
    expect(result).toBe(payload);
  });

  it('omits invalid limits and preserves false flags', async () => {
    vi.stubEnv('VITE_PRACTICE_QUEUE_LIMIT', '-2');
    const payload = { ok: true } as any;
    getMock.mockResolvedValue({ data: payload });

    const { fetchPracticeQueue } = await loadPractice();
    await fetchPracticeQueue('all');

    expect(getMock).toHaveBeenCalledWith('/api/practice/queue', {
      params: {
        include_failed_attempt: false,
      },
    });
  });

  it('omits non-finite limits', async () => {
    vi.stubEnv('VITE_PRACTICE_QUEUE_LIMIT', 'Infinity');
    const payload = { ok: true } as any;
    getMock.mockResolvedValue({ data: payload });

    const { fetchPracticeQueue } = await loadPractice();
    await fetchPracticeQueue(undefined, false);

    expect(getMock).toHaveBeenCalledWith('/api/practice/queue', {
      params: {
        include_failed_attempt: false,
      },
    });
  });

  it('defaults to no limit when env is unset', async () => {
    const payload = { ok: true } as any;
    getMock.mockResolvedValue({ data: payload });

    const { fetchPracticeQueue } = await loadPractice();
    await fetchPracticeQueue('lichess');

    expect(getMock).toHaveBeenCalledWith('/api/practice/queue', {
      params: {
        source: 'lichess',
        include_failed_attempt: false,
      },
    });
  });

  it('submits practice attempts', async () => {
    const payload = { ok: true } as any;
    postMock.mockResolvedValue({ data: payload });

    const { submitPracticeAttempt } = await loadPractice();
    const result = await submitPracticeAttempt({
      tactic_id: 1,
      position_id: 2,
      attempted_uci: 'e2e4',
    });

    expect(postMock).toHaveBeenCalledWith('/api/practice/attempt', {
      tactic_id: 1,
      position_id: 2,
      attempted_uci: 'e2e4',
    });
    expect(result).toBe(payload);
  });
});
