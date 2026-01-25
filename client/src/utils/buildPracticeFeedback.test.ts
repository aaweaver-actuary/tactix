import { describe, it, expect } from 'vitest';
import buildPracticeFeedback from './buildPracticeFeedback';
import type { PracticeAttemptResponse } from '../api';

describe('buildPracticeFeedback', () => {
  it('returns feedback with best move when provided', () => {
    const practiceFeedback: PracticeAttemptResponse = {
      attempted_uci: 'e2e4',
      best_uci: 'e7e5',
    } as PracticeAttemptResponse;

    expect(buildPracticeFeedback(practiceFeedback)).toBe(
      'You played e2e4 · best e7e5',
    );
  });

  it('falls back to "--" when best move is missing', () => {
    const practiceFeedback: PracticeAttemptResponse = {
      attempted_uci: 'g1f3',
      best_uci: '',
    } as PracticeAttemptResponse;

    expect(buildPracticeFeedback(practiceFeedback)).toBe(
      'You played g1f3 · best --',
    );
  });

  it('falls back to "--" when best move is null or undefined', () => {
    const practiceFeedback: PracticeAttemptResponse = {
      attempted_uci: 'd2d4',
      best_uci: undefined,
    } as PracticeAttemptResponse;

    expect(buildPracticeFeedback(practiceFeedback)).toBe(
      'You played d2d4 · best --',
    );
  });
});
