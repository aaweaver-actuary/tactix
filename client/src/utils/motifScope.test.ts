import { describe, expect, it } from 'vitest';
import { isAllowedMotifFilter, isScopedMotif } from './motifScope';

describe('motifScope utilities', () => {
  it('accepts scoped motifs', () => {
    expect(isScopedMotif('hanging_piece')).toBe(true);
    expect(isScopedMotif('mate')).toBe(true);
  });

  it('rejects non-scoped motifs', () => {
    expect(isScopedMotif('all')).toBe(false);
    expect(isScopedMotif('pin')).toBe(false);
    expect(isScopedMotif('initiative')).toBe(false);
    expect(isScopedMotif(null)).toBe(false);
    expect(isScopedMotif(undefined)).toBe(false);
  });

  it('allows empty or all filters', () => {
    expect(isAllowedMotifFilter(null)).toBe(true);
    expect(isAllowedMotifFilter(undefined)).toBe(true);
    expect(isAllowedMotifFilter('all')).toBe(true);
  });

  it('allows scoped motif filters and rejects others', () => {
    expect(isAllowedMotifFilter('hanging_piece')).toBe(true);
    expect(isAllowedMotifFilter('mate')).toBe(true);
    expect(isAllowedMotifFilter('pin')).toBe(false);
    expect(isAllowedMotifFilter('initiative')).toBe(false);
  });
});
