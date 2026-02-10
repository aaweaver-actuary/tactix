import {
  applyPracticeAttemptResult,
  getPracticeProgressPercent,
  getPracticeStreakPercent,
  resetPracticeSessionStats,
  updatePracticeSessionStats,
} from './practiceSession';

describe('practiceSession', () => {
  it('resets stats with provided total', () => {
    const stats = resetPracticeSessionStats(12);
    expect(stats).toEqual({
      completed: 0,
      total: 12,
      streak: 0,
      bestStreak: 0,
    });
  });

  it('updates stats for correct and incorrect attempts', () => {
    const start = resetPracticeSessionStats(5);
    const afterCorrect = updatePracticeSessionStats(start, true);
    expect(afterCorrect).toEqual({
      completed: 1,
      total: 5,
      streak: 1,
      bestStreak: 1,
    });

    const afterCorrectAgain = updatePracticeSessionStats(afterCorrect, true);
    expect(afterCorrectAgain).toEqual({
      completed: 2,
      total: 5,
      streak: 2,
      bestStreak: 2,
    });

    const afterIncorrect = updatePracticeSessionStats(afterCorrectAgain, false);
    expect(afterIncorrect).toEqual({
      completed: 3,
      total: 5,
      streak: 0,
      bestStreak: 2,
    });
  });

  it('applies reschedule logic for practice attempts', () => {
    const start = resetPracticeSessionStats(3);
    const correctResult = applyPracticeAttemptResult(start, { correct: true });
    expect(correctResult.stats.total).toBe(3);
    expect(correctResult.shouldReschedule).toBe(false);

    const rescheduled = applyPracticeAttemptResult(correctResult.stats, {
      correct: true,
      rescheduled: true,
    });
    expect(rescheduled.stats.total).toBe(4);
    expect(rescheduled.shouldReschedule).toBe(true);
  });

  it('calculates bounded progress percent', () => {
    const stats = { completed: 4, total: 10, streak: 0, bestStreak: 0 };
    expect(getPracticeProgressPercent(stats)).toBe(40);

    const empty = { completed: 0, total: 0, streak: 0, bestStreak: 0 };
    expect(getPracticeProgressPercent(empty)).toBe(0);

    const overflow = { completed: 20, total: 10, streak: 0, bestStreak: 0 };
    expect(getPracticeProgressPercent(overflow)).toBe(100);
  });

  it('calculates bounded streak percent', () => {
    const stats = { completed: 2, total: 5, streak: 2, bestStreak: 3 };
    expect(getPracticeStreakPercent(stats)).toBe(67);

    const empty = { completed: 0, total: 5, streak: 0, bestStreak: 0 };
    expect(getPracticeStreakPercent(empty)).toBe(0);

    const overflow = { completed: 0, total: 5, streak: 10, bestStreak: 4 };
    expect(getPracticeStreakPercent(overflow)).toBe(100);
  });
});
