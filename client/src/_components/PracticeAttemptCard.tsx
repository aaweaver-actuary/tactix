import BaseButton from './BaseButton';
import BaseCard, { BaseCardDragProps } from './BaseCard';
import Badge from './Badge';
import Text from './Text';
import type { PracticeQueueItem } from '../api';
import type { PracticeSessionStats } from '../utils/practiceSession';
import PracticeSessionProgress from './PracticeSessionProgress';

interface PracticeAttemptCardProps extends BaseCardDragProps {
  currentPractice: PracticeQueueItem | null;
  practiceSession: PracticeSessionStats;
  practiceLoading: boolean;
  practiceModalOpen: boolean;
  onStartPractice: () => void;
}

export default function PracticeAttemptCard({
  currentPractice,
  practiceSession,
  practiceLoading,
  practiceModalOpen,
  onStartPractice,
  ...dragProps
}: PracticeAttemptCardProps) {
  const hasPractice = Boolean(currentPractice);
  const isComplete =
    !practiceLoading && !hasPractice && practiceSession.total > 0;
  const buttonLabel = practiceModalOpen
    ? 'Continue practice'
    : 'Start practice';

  return (
    <BaseCard
      className="p-4"
      header={
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-display text-sand">Practice attempt</h3>
            <Text value="Daily tactics ready to review." />
          </div>
          {currentPractice ? <Badge label={currentPractice.motif} /> : null}
        </div>
      }
      contentClassName="pt-3"
      {...dragProps}
    >
      <PracticeSessionProgress stats={practiceSession} />
      {practiceLoading ? (
        <Text value="Loading daily practice set..." />
      ) : isComplete ? (
        <Text value="Daily set complete. Great work." />
      ) : hasPractice ? (
        <div className="flex flex-wrap items-center gap-3">
          <Text value="Your next tactic is ready." />
          <BaseButton
            className="rounded-md border border-white/10 px-3 py-2 text-xs text-sand/80 hover:border-white/30"
            onClick={onStartPractice}
            data-testid="practice-start"
          >
            {buttonLabel}
          </BaseButton>
        </div>
      ) : (
        <Text value="No practice items queued yet." />
      )}
    </BaseCard>
  );
}
