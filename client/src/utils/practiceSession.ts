export type PracticeSessionStats = {
  completed: number;
  total: number;
  streak: number;
  bestStreak: number;
};

export type PracticeAttemptOutcome = {
  correct: boolean;
  rescheduled?: boolean | null;
};

export type PracticeAttemptSessionUpdate = {
  stats: PracticeSessionStats;
  shouldReschedule: boolean;
};

export function resetPracticeSessionStats(total: number): PracticeSessionStats {
  return {
    completed: 0,
    total,
    streak: 0,
    bestStreak: 0,
  };
}

export function updatePracticeSessionStats(
  stats: PracticeSessionStats,
  correct: boolean,
): PracticeSessionStats {
  const nextStreak = correct ? stats.streak + 1 : 0;
  return {
    ...stats,
    completed: stats.completed + 1,
    streak: nextStreak,
    bestStreak: Math.max(stats.bestStreak, nextStreak),
  };
}

export function applyPracticeAttemptResult(
  stats: PracticeSessionStats,
  outcome: PracticeAttemptOutcome,
): PracticeAttemptSessionUpdate {
  const nextStats = updatePracticeSessionStats(stats, outcome.correct);
  const shouldReschedule = outcome.rescheduled ?? !outcome.correct;
  const total = shouldReschedule ? nextStats.total + 1 : nextStats.total;
  return { stats: { ...nextStats, total }, shouldReschedule };
}

export function getPracticeProgressPercent(
  stats: PracticeSessionStats,
): number {
  if (stats.total <= 0) return 0;
  const percent = Math.round((stats.completed / stats.total) * 100);
  return Math.min(100, Math.max(0, percent));
}

export function getPracticeStreakPercent(stats: PracticeSessionStats): number {
  if (stats.bestStreak <= 0) return 0;
  const percent = Math.round((stats.streak / stats.bestStreak) * 100);
  return Math.min(100, Math.max(0, percent));
}
