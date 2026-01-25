import Badge from './Badge';
import Text from './Text';
import {
  PracticeSessionStats,
  getPracticeProgressPercent,
  getPracticeStreakPercent,
} from '../utils/practiceSession';

interface PracticeSessionProgressProps {
  stats: PracticeSessionStats;
}

/**
 * Displays the current practice session streaks and progress.
 */
export default function PracticeSessionProgress({
  stats,
}: PracticeSessionProgressProps) {
  const progressPercent = getPracticeProgressPercent(stats);
  const streakPercent = getPracticeStreakPercent(stats);

  return (
    <div
      className="rounded-md border border-white/10 bg-white/5 p-3 space-y-2"
      data-testid="practice-session-progress"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1" data-testid="practice-session-summary">
          <Text value="Session progress" />
          <Text
            value={`${stats.completed} of ${stats.total} attempts`}
            size="xs"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span data-testid="practice-session-streak">
            <Badge label={`Streak ${stats.streak}`} />
          </span>
          <span data-testid="practice-session-best">
            <Badge label={`Best ${stats.bestStreak}`} />
          </span>
        </div>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-white/10"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progressPercent}
        data-testid="practice-progress-bar"
      >
        <div
          className="h-full bg-teal transition-all"
          style={{ width: `${progressPercent}%` }}
          data-testid="practice-progress-fill"
        />
      </div>
      <Text value={`${stats.completed} / ${stats.total} complete`} size="xs" />
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs text-sand/60">
          <span>Streak momentum</span>
          <span>{`${stats.streak} / ${stats.bestStreak}`}</span>
        </div>
        <div
          className="h-2 w-full overflow-hidden rounded-full bg-white/10"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={streakPercent}
          data-testid="practice-streak-progress"
        >
          <div
            className="h-full bg-rust/80 transition-all"
            style={{ width: `${streakPercent}%` }}
            data-testid="practice-streak-fill"
          />
        </div>
      </div>
    </div>
  );
}
