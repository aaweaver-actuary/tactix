import { describe, it, expect } from 'vitest';
import isPiecePlayable from './isPiecePlayable';

describe('isPiecePlayable', () => {
  const startFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  const blackToMoveFen =
    'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1';

  it('returns false when no fen is available', () => {
    const currentPractice = { fen: '' } as any;
    const playable = isPiecePlayable('', currentPractice);
    expect(playable({ piece: 'wP', sourceSquare: 'e2' })).toBe(false);
  });

  it('uses practiceFen when provided', () => {
    const currentPractice = { fen: blackToMoveFen } as any;
    const playable = isPiecePlayable(startFen, currentPractice);
    expect(playable({ piece: 'wP', sourceSquare: 'e2' })).toBe(true);
    expect(playable({ piece: 'bP', sourceSquare: 'e7' })).toBe(false);
  });

  it('falls back to currentPractice.fen when practiceFen is empty', () => {
    const currentPractice = { fen: blackToMoveFen } as any;
    const playable = isPiecePlayable('', currentPractice);
    expect(playable({ piece: 'bP', sourceSquare: 'e7' })).toBe(true);
    expect(playable({ piece: 'wP', sourceSquare: 'e2' })).toBe(false);
  });

  it('handles piece as object with color', () => {
    const currentPractice = { fen: startFen } as any;
    const playable = isPiecePlayable('', currentPractice);
    expect(
      playable({ piece: { color: 'w', type: 'p' }, sourceSquare: 'e2' }),
    ).toBe(true);
    expect(
      playable({ piece: { color: 'b', type: 'p' }, sourceSquare: 'e7' }),
    ).toBe(false);
  });
});
