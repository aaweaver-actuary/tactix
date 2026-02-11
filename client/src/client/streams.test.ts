import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { openEventStream } from './streams';
import { getAuthHeaders } from '../utils/getAuthHeaders';

vi.mock('../utils/getAuthHeaders', () => ({
  getAuthHeaders: vi.fn(),
}));

describe('client/streams', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.mocked(getAuthHeaders).mockReturnValue({
      Authorization: 'Bearer test-token',
    });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('returns a reader when the stream is ready', async () => {
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new Uint8Array([1]));
        controller.close();
      },
    });
    fetchMock.mockResolvedValue(new Response(stream, { status: 200 }));

    const reader = await openEventStream(
      '/api/jobs/stream?job=test',
      new AbortController().signal,
    );

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/jobs/stream?job=test',
      expect.objectContaining({
        headers: { Authorization: 'Bearer test-token' },
        signal: expect.any(AbortSignal),
      }),
    );
    expect(reader.read).toBeDefined();
  });

  it('throws when the response is not ok', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      body: null,
    });

    await expect(
      openEventStream(
        '/api/jobs/stream?job=test',
        new AbortController().signal,
      ),
    ).rejects.toThrow('Stream failed with status 500');
  });
});
