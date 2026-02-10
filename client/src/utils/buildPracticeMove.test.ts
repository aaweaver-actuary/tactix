import { describe, expect, it } from 'vitest';
import buildPracticeMove from './buildPracticeMove';

describe('buildPracticeMove', () => {
  const startFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  const promotionFen = 'k7/4P3/8/8/8/8/8/7K w - - 0 1';

  it('returns null for too-short input', () => {
    expect(buildPracticeMove(startFen, 'e2')).toBeNull();
  });

  it('returns null for illegal moves', () => {
    expect(buildPracticeMove(startFen, 'e2e5')).toBeNull();
  });

  it('returns move data for legal UCI input', () => {
    const result = buildPracticeMove(startFen, 'e2e4');
    expect(result).toEqual({
      uci: 'e2e4',
      nextFen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
      from: 'e2',
      to: 'e4',
    });
  });

  it('defaults to queen promotion when none is provided', () => {
    const result = buildPracticeMove(promotionFen, 'e7e8');
    expect(result).toEqual({
      uci: 'e7e8q',
      nextFen: 'k3Q3/8/8/8/8/8/8/7K b - - 0 1',
      from: 'e7',
      to: 'e8',
    });
  });

  it('respects explicit promotion choices', () => {
    const result = buildPracticeMove(promotionFen, 'e7e8n');
    expect(result).toEqual({
      uci: 'e7e8n',
      nextFen: 'k3N3/8/8/8/8/8/8/7K b - - 0 1',
      from: 'e7',
      to: 'e8',
    });
  });
});
