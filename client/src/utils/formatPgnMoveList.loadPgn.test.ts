import { describe, expect, it, vi } from 'vitest';

describe('formatPgnMoveList (loadPgn path)', () => {
  it('uses chess.js history when loadPgn returns true', async () => {
    vi.resetModules();
    vi.doMock('chess.js', () => ({
      Chess: class {
        loadPgn() {
          return true;
        }
        history() {
          return ['e4', 'e5', 'Nf3'];
        }
      },
    }));

    const mod = await import('./formatPgnMoveList');
    expect(mod.default('1. e4 e5 2. Nf3')).toEqual(['1. e4 e5', '2. Nf3']);
  });
});
