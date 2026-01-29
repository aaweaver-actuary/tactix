import type { CSSProperties, Dispatch, SetStateAction } from 'react';
import { Chessboard } from 'react-chessboard';
import { PracticeAttemptResponse, PracticeQueueItem } from '../api';
import isPiecePlayable from '../utils/isPiecePlayable';
import buildPracticeFeedback from '../utils/buildPracticeFeedback';
import Badge from './Badge';
import BaseCard from './BaseCard';
import PracticeAttemptButton from './PracticeAttemptButton';
import PracticeMoveInput from './PracticeMoveInput';
import PracticeSessionProgress from './PracticeSessionProgress';
import Text from './Text';
import type { PracticeSessionStats } from '../utils/practiceSession';

interface PracticeAttemptCardProps {
  currentPractice: PracticeQueueItem | null;
  practiceSession: PracticeSessionStats;
  practiceFen: string;
  practiceMove: string;
  practiceSubmitting: boolean;
  practiceFeedback: PracticeAttemptResponse | null;
  practiceSubmitError: string | null;
  practiceHighlightStyles: Record<string, CSSProperties>;
  practiceOrientation: 'white' | 'black';
  setPracticeMove: Dispatch<SetStateAction<string>>;
  handlePracticeAttempt: (overrideMove?: string) => Promise<void>;
  handlePracticeDrop: (from: string, to: string, piece: string) => boolean;
}

export default function PracticeAttemptCard({
  currentPractice,
  practiceSession,
  practiceFen,
  practiceMove,
  practiceSubmitting,
  practiceFeedback,
  practiceSubmitError,
  practiceHighlightStyles,
  practiceOrientation,
  setPracticeMove,
  handlePracticeAttempt,
  handlePracticeDrop,
}: PracticeAttemptCardProps) {
  return (
    <BaseCard
      className="p-4"
      collapsible={false}
      header={
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-display text-sand">Practice attempt</h3>
            <Text value="Play the best move for the current tactic." />
          </div>
          {currentPractice ? <Badge label={currentPractice.motif} /> : null}
        </div>
      }
      contentClassName="pt-3"
    >
      <PracticeSessionProgress stats={practiceSession} />
      {currentPractice ? (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
            <div className="rounded-lg border border-white/10 bg-white/5 p-3">
              <Chessboard
                id="practice-board"
                position={practiceFen || currentPractice.fen}
                onPieceDrop={handlePracticeDrop}
                boardOrientation={practiceOrientation}
                arePiecesDraggable={!practiceSubmitting}
                isDraggablePiece={isPiecePlayable(practiceFen, currentPractice)}
                customSquareStyles={practiceHighlightStyles}
              />
              <Text mt="2" value="Legal moves only. Drag a piece to submit." />
            </div>
            <div className="space-y-3">
              <div className="space-y-1">
                <Text value="FEN" />
                <Text value={currentPractice.fen} mode="monospace" />
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-sand/70">
                <Badge
                  label={`Move ${currentPractice.move_number}.${currentPractice.ply}`}
                />
                <Badge label={`Best ${currentPractice.best_uci || '--'}`} />
                {currentPractice.clock_seconds !== null ? (
                  <Badge label={`${currentPractice.clock_seconds}s`} />
                ) : null}
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <PracticeMoveInput
                  practiceMove={practiceMove}
                  setPracticeMove={setPracticeMove}
                  practiceSubmitting={practiceSubmitting}
                />
                <PracticeAttemptButton
                  handlePracticeAttempt={handlePracticeAttempt}
                  practiceSubmitting={practiceSubmitting}
                />
              </div>
              {practiceSubmitError ? (
                <Text mode="error" value={practiceSubmitError} />
              ) : null}
              {practiceFeedback ? (
                <div className="rounded-md border border-white/10 bg-white/5 p-3 text-sm">
                  <div className="flex items-center gap-2">
                    <Badge
                      label={practiceFeedback.correct ? 'Correct' : 'Missed'}
                    />
                    <span className="text-sand/80">
                      {practiceFeedback.message}
                    </span>
                  </div>
                  <PracticeFeedbackExplanation feedback={practiceFeedback} />
                  <PracticeFeedback feedback={practiceFeedback} />
                </div>
              ) : null}
            </div>
          </div>
        </>
      ) : (
        <Text value="No practice items queued yet." />
      )}
    </BaseCard>
  );
}

function PracticeFeedbackExplanation({
  feedback,
}: {
  feedback: PracticeAttemptResponse;
}) {
  return feedback.explanation ? (
    <Text mt="2" value={feedback.explanation} />
  ) : null;
}

function PracticeFeedback({
  feedback,
}: {
  feedback: PracticeAttemptResponse;
}): JSX.Element {
  return (
    <Text
      mt="2"
      mode="monospace"
      size="xs"
      value={buildPracticeFeedback(feedback)}
    />
  );
}
