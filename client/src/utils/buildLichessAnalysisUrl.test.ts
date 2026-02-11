import { describe, expect, it } from 'vitest';
import buildLichessAnalysisUrl from './buildLichessAnalysisUrl';

describe('buildLichessAnalysisUrl', () => {
  it('returns null for empty input', () => {
    expect(buildLichessAnalysisUrl('')).toBeNull();
    expect(buildLichessAnalysisUrl('   ')).toBeNull();
  });

  it('returns null for invalid PGN', () => {
    expect(buildLichessAnalysisUrl('not a pgn')).toBeNull();
  });

  it('builds analysis urls with color and anchors', () => {
    const pgn = '1. e4 e5 2. Nf3 Nc6';
    const url = buildLichessAnalysisUrl(pgn, { anchorPly: 3 });

    expect(url).toContain('https://lichess.org/analysis/pgn');
    expect(url).toContain('?color=white');
    expect(url).toContain('#3');
  });

  it('normalizes negative anchors and uses black to move', () => {
    const pgn = '1. e4';
    const url = buildLichessAnalysisUrl(pgn, { anchorPly: -2 });

    expect(url).toContain('?color=black');
    expect(url).not.toContain('#');
  });
});
