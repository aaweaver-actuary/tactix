import { describe, expect, it, vi, beforeEach } from 'vitest';
import submitPracticeAttempt from './submitPracticeAttempt';
import { client } from '../api';

vi.mock('../api', () => ({
  client: {
    post: vi.fn(),
  },
}));

describe('submitPracticeAttempt', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts payload to the practice attempt endpoint and returns data', async () => {
    const payload = { foo: 'bar' } as any;
    const responseData = { ok: true } as any;

    (client.post as any).mockResolvedValue({ data: responseData });

    const result = await submitPracticeAttempt(payload);

    expect(client.post).toHaveBeenCalledWith('/api/practice/attempt', payload);
    expect(result).toBe(responseData);
  });

  it('propagates errors from the client', async () => {
    const payload = { foo: 'bar' } as any;
    const error = new Error('network');

    (client.post as any).mockRejectedValue(error);

    await expect(submitPracticeAttempt(payload)).rejects.toThrow('network');
  });
});
