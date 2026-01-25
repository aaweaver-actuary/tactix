import { describe, expect, it, vi, beforeEach } from 'vitest';
import triggerMigrations from './triggerMigrations';

const postMock = vi.hoisted(() => vi.fn());

vi.mock('../api', () => ({
  client: {
    post: postMock,
  },
}));

describe('triggerMigrations', () => {
  beforeEach(() => {
    postMock.mockReset();
  });

  it('posts to migrations endpoint with source param', async () => {
    const data = {
      status: 'ok',
      result: { source: 'cli', schema_version: 3 },
    };
    postMock.mockResolvedValueOnce({ data });

    const res = await triggerMigrations('cli');

    expect(postMock).toHaveBeenCalledWith('/api/jobs/migrations', null, {
      params: { source: 'cli' },
    });
    expect(res).toEqual(data);
  });

  it('posts to migrations endpoint with undefined source when omitted', async () => {
    const data = {
      status: 'ok',
      result: { source: 'default', schema_version: 1 },
    };
    postMock.mockResolvedValueOnce({ data });

    const res = await triggerMigrations();

    expect(postMock).toHaveBeenCalledWith('/api/jobs/migrations', null, {
      params: { source: undefined },
    });
    expect(res).toEqual(data);
  });
});
