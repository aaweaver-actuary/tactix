import type { CSSProperties, RefObject } from 'react';
import BaseChessboard from './BaseChessboard';
import { PracticeAttemptResponse, PracticeQueueItem } from '../api';
import isPiecePlayable from '../utils/isPiecePlayable';
import buildPracticeFeedback from '../utils/buildPracticeFeedback';
import Badge from './Badge';
import ChessboardPanel from './ChessboardPanel';
import ModalHeader from './ModalHeader';
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
    void handlePracticeAttempt();
  };

  return (
    <div className="space-y-4">
      <ModalHeader
        title="Daily practice"
        description="Play the best move for each tactic."
        className="flex-wrap"
        rightSlot={
          currentPractice ? <Badge label={currentPractice.motif} /> : null
        }
      />
      <PracticeSessionProgress stats={practiceSession} />
      {currentPractice ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr] practice-context-grid">
          <ChessboardPanel className="practice-context-board">
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
          </ChessboardPanel>
          <div className="space-y-3 practice-context-details">
            <div className="space-y-1">
              <Text value="FEN" />
              <Text value={currentPractice.fen} mode="monospace" />
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-sand/70">
              <Badge
                label={`Move ${currentPractice.move_number}.${currentPractice.ply}`}
              />
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
              <PracticeFeedbackCard feedback={practiceFeedback} />
            ) : null}
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <Text value="Daily set complete. Check back tomorrow." />
          {practiceFeedback ? (
            <PracticeFeedbackCard feedback={practiceFeedback} />
          ) : null}
        </div>
      )}
    </div>
  );
}

function PracticeFeedbackCard({
  feedback,
}: {
  feedback: PracticeAttemptResponse;
}): JSX.Element {
  return (
    <div className="rounded-md border border-white/10 bg-white/5 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span data-testid="practice-best-move">
          <Badge label={`Best ${feedback.best_uci || '--'}`} />
        </span>
        <Badge label={feedback.correct ? 'Correct' : 'Missed'} />
        <span className="text-sand/80">{feedback.message}</span>
      </div>
      <PracticeFeedbackExplanation feedback={feedback} />
      <PracticeFeedback feedback={feedback} />
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
