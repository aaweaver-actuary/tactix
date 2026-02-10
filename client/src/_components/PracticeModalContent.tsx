import type { CSSProperties, RefObject } from 'react';
import BaseChessboard from './BaseChessboard';
import { PracticeAttemptResponse, PracticeQueueItem } from '../api';
import isPiecePlayable from '../utils/isPiecePlayable';
import buildPracticeFeedback from '../utils/buildPracticeFeedback';
import Badge from './Badge';
import PracticeAttemptButton from './PracticeAttemptButton';
import PracticeMoveInput from './PracticeMoveInput';
import PracticeSessionProgress from './PracticeSessionProgress';
import Text from './Text';
import type { PracticeSessionStats } from '../utils/practiceSession';

interface PracticeModalContentProps {
  currentPractice: PracticeQueueItem | null;
  practiceSession: PracticeSessionStats;
  practiceFen: string;
  practiceMove: string;
  practiceMoveRef: RefObject<HTMLInputElement>;
  practiceSubmitting: boolean;
  practiceFeedback: PracticeAttemptResponse | null;
  practiceSubmitError: string | null;
  practiceHighlightStyles: Record<string, CSSProperties>;
  practiceOrientation: 'white' | 'black';
  onPracticeMoveChange: (value: string) => void;
  handlePracticeAttempt: (overrideMove?: string) => Promise<void>;
  handlePracticeDrop: (from: string, to: string, piece: string) => boolean;
}

export default function PracticeModalContent({
  currentPractice,
  practiceSession,
  practiceFen,
  practiceMove,
  practiceMoveRef,
  practiceSubmitting,
  practiceFeedback,
  practiceSubmitError,
  practiceHighlightStyles,
  practiceOrientation,
  onPracticeMoveChange,
  handlePracticeAttempt,
  handlePracticeDrop,
}: PracticeModalContentProps) {
  const handleInputSubmit = (move: string) => {
    void handlePracticeAttempt(move);
  };

  const handleAttemptClick = () => {
    void handlePracticeAttempt(practiceMoveRef.current?.value);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Text mode="uppercase" value="Daily practice" />
          <div className="text-xs text-sand/60">
            Play the best move for each tactic.
          </div>
        </div>
        {currentPractice ? <Badge label={currentPractice.motif} /> : null}
      </div>
      <PracticeSessionProgress stats={practiceSession} />
      {currentPractice ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
          <div className="rounded-lg border border-white/10 bg-white/5 p-3">
            <BaseChessboard
              id="practice-board"
              position={practiceFen || currentPractice.fen}
              onPieceDrop={handlePracticeDrop}
              boardOrientation={practiceOrientation}
              arePiecesDraggable={!practiceSubmitting}
              isDraggablePiece={isPiecePlayable(practiceFen, currentPractice)}
              boardWidth={320}
              showBoardNotation
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
              {practiceFeedback ? (
                <span data-testid="practice-best-move">
                  <Badge label={`Best ${practiceFeedback.best_uci || '--'}`} />
                </span>
              ) : null}
              {currentPractice.clock_seconds !== null ? (
                <Badge label={`${currentPractice.clock_seconds}s`} />
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <PracticeMoveInput
                practiceMove={practiceMove}
                onPracticeMoveChange={onPracticeMoveChange}
                onPracticeSubmit={handleInputSubmit}
                practiceSubmitting={practiceSubmitting}
                inputRef={practiceMoveRef}
              />
              <PracticeAttemptButton
                onPracticeAttempt={handleAttemptClick}
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
      ) : (
        <Text value="Daily set complete. Check back tomorrow." />
      )}
    </div>
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
