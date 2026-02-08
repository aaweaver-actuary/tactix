import type { CSSProperties, RefObject } from 'react';
import { Chessboard } from 'react-chessboard';
import { PracticeAttemptResponse, PracticeQueueItem } from '../api';
import isPiecePlayable from '../utils/isPiecePlayable';
import buildPracticeFeedback from '../utils/buildPracticeFeedback';
import Badge from './Badge';
import BaseCard, { BaseCardDragProps } from './BaseCard';
import PracticeAttemptButton from './PracticeAttemptButton';
import PracticeMoveInput from './PracticeMoveInput';
import PracticeSessionProgress from './PracticeSessionProgress';
import Text from './Text';
import type { PracticeSessionStats } from '../utils/practiceSession';

const listudyBoardStyle: CSSProperties = {
  backgroundImage: 'url(/boards/listudy-brown.svg)',
  backgroundSize: 'cover',
  backgroundPosition: 'center',
  borderRadius: '14px',
  overflow: 'hidden',
  boxShadow: '0 12px 32px rgba(0, 0, 0, 0.35)',
};

// Squares stay transparent to let the SVG board art show through.
const listudyLightSquareStyle: CSSProperties = {
  backgroundColor: 'transparent',
};

const listudyDarkSquareStyle: CSSProperties = {
  backgroundColor: 'transparent',
};

const listudyNotationStyle: CSSProperties = {
  color: '#203038',
  fontWeight: 600,
  fontFamily: '"Space Grotesk", "Helvetica Neue", sans-serif',
};

const listudyPieces = {
  bB: buildPiece('bB'),
  bK: buildPiece('bK'),
  bN: buildPiece('bN'),
  bP: buildPiece('bP'),
  bQ: buildPiece('bQ'),
  bR: buildPiece('bR'),
  wB: buildPiece('wB'),
  wK: buildPiece('wK'),
  wN: buildPiece('wN'),
  wP: buildPiece('wP'),
  wQ: buildPiece('wQ'),
  wR: buildPiece('wR'),
};

function buildPiece(pieceId: string) {
  const Piece = ({ squareWidth }: { squareWidth: number }) => (
    <img
      src={`/pieces/cburnett/${pieceId}.svg`}
      alt={pieceId}
      draggable={false}
      style={{
        width: squareWidth,
        height: squareWidth,
        userSelect: 'none',
        filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.35))',
      }}
    />
  );

  Piece.displayName = `ListudyPiece_${pieceId}`;
  return Piece;
}

interface PracticeAttemptCardProps extends BaseCardDragProps {
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

export default function PracticeAttemptCard({
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
  ...dragProps
}: PracticeAttemptCardProps) {
  const handleInputSubmit = (move: string) => {
    void handlePracticeAttempt(move);
  };

  const handleAttemptClick = () => {
    void handlePracticeAttempt(practiceMoveRef.current?.value);
  };

  return (
    <BaseCard
      className="p-4"
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
      {...dragProps}
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
                boardWidth={320}
                showBoardNotation
                customNotationStyle={listudyNotationStyle}
                customBoardStyle={listudyBoardStyle}
                customLightSquareStyle={listudyLightSquareStyle}
                customDarkSquareStyle={listudyDarkSquareStyle}
                customPieces={listudyPieces}
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
