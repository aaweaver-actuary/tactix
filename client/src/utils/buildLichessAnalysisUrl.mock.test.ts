import { describe, expect, it, vi } from 'vitest';

describe('buildLichessAnalysisUrl (mocked history)', () => {
  it('returns null when history disappears after load', async () => {
    let historyCalls = 0;
    vi.resetModules();
    vi.doMock('chess.js', () => ({
      Chess: class {
        loadPgn() {
          return true;
        }
        history() {
          historyCalls += 1;
          return historyCalls === 1 ? ['e4'] : [];
        }
        turn() {
          return 'w';
        }
      },
    }));

    const mod = await import('./buildLichessAnalysisUrl');
    expect(mod.default('1. e4')).toBeNull();
  });
});
