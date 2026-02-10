import type { CSSProperties, RefObject } from 'react';
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Chess } from 'chess.js';
import type {
  DashboardPayload,
  PracticeAttemptResponse,
  PracticeQueueItem,
} from '../api';
import BaseChessboard from './BaseChessboard';
import Badge from './Badge';
import BaseButton from './BaseButton';
import ChessboardPanel from './ChessboardPanel';
import ModalCloseButton from './ModalCloseButton';
import ModalHeader from './ModalHeader';
import ModalShell from './ModalShell';
import Text from './Text';
import type { PracticeSessionStats } from '../utils/practiceSession';
import PracticeModalContent from './PracticeModalContent';

type PositionEntry = DashboardPayload['positions'][number];

interface ChessboardModalProps {
  open: boolean;
  position: PositionEntry | null;
  practice?: PracticeModalState | null;
  onClose: () => void;
}

interface PracticeModalState {
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

const getOrientation = (fen: string | null) => {
  const side = fen?.split(' ')[1];
  return side === 'b' ? 'black' : 'white';
};

const normalizeFen = (fen: string) => {
  try {
    const board = new Chess(fen);
    return board.fen();
  } catch {
    return null;
  }
};

export default function ChessboardModal({
  open,
  position,
  practice,
  onClose,
}: ChessboardModalProps) {
  const [draftFen, setDraftFen] = useState(position?.fen ?? '');
  const [activeFen, setActiveFen] = useState(position?.fen ?? '');
  const [fenError, setFenError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const baseFen = position?.fen ?? '';
    setDraftFen(baseFen);
    setActiveFen(baseFen);
    setFenError(null);
  }, [open, position?.fen]);

  if (!open) {
    return null;
  }

  if (practice) {
    return createPortal(
      <ModalShell
        testId="chessboard-modal"
        onClose={onClose}
        panelClassName="max-w-5xl"
      >
        <ModalHeader
          title="Practice board"
          rightSlot={
            <ModalCloseButton
              onClick={onClose}
              testId="chessboard-modal-close"
            />
          }
        />
        <div className="mt-4">
          <PracticeModalContent {...practice} />
        </div>
      </ModalShell>,
      document.body,
    );
  }

  const handleFenApply = () => {
    const nextFen = draftFen.trim();
    if (!nextFen) {
      setFenError('Enter a FEN string to update the board.');
      return;
    }
    const normalized = normalizeFen(nextFen);
    if (!normalized) {
      setFenError(
        'Invalid FEN. Check piece placement, side to move, and castling rights.',
      );
      return;
    }
    setFenError(null);
    setActiveFen(normalized);
  };

  const handleFenReset = () => {
    const baseFen = position?.fen ?? '';
    setDraftFen(baseFen);
    setActiveFen(baseFen);
    setFenError(null);
  };

  const fen = activeFen || position?.fen || '';
  const orientation = getOrientation(fen || null);
  const moveLabel = `Move ${position?.move_number ?? '--'}`;
  const sanLabel = position?.san ? `SAN ${position.san}` : 'SAN --';
  const clockLabel = `${position?.clock_seconds ?? '--'}s`;
  return createPortal(
    <ModalShell
      testId="chessboard-modal"
      onClose={onClose}
      panelClassName="max-w-4xl"
    >
      <ModalHeader
        title="Position board"
        description="Review the selected position in context"
        className="flex-wrap"
        rightSlot={
          <ModalCloseButton onClick={onClose} testId="chessboard-modal-close" />
        }
      />

      {!position ? (
        <div className="mt-4 text-sm text-sand/70">
          Select a position to view the board.
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-[360px_1fr]">
          <ChessboardPanel data-testid="chessboard-modal-board">
            <BaseChessboard
              id="chessboard-modal-board"
              position={fen}
              boardOrientation={orientation}
              boardWidth={340}
              showBoardNotation
            />
          </ChessboardPanel>
          <div className="space-y-4">
            <div>
              <Text value="FEN" />
              <Text value={fen || '--'} mode="monospace" size="xs" />
            </div>
            <div className="space-y-2">
              <Text value="Edit position" />
              <textarea
                data-testid="browser-fen-input"
                value={draftFen}
                onChange={(event) => {
                  setDraftFen(event.target.value);
                  if (fenError) setFenError(null);
                }}
                placeholder="Paste a full FEN string"
                rows={4}
                className="w-full rounded-md border border-white/10 bg-slate-950/70 p-2 text-xs text-sand/80 font-mono"
              />
              <div className="flex flex-wrap gap-2">
                <BaseButton
                  data-testid="browser-fen-apply"
                  onClick={handleFenApply}
                  className="rounded-md bg-teal px-3 py-1 text-xs font-semibold text-slate-950"
                >
                  Apply position
                </BaseButton>
                <BaseButton
                  data-testid="browser-fen-reset"
                  onClick={handleFenReset}
                  className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
                >
                  Reset
                </BaseButton>
              </div>
              {fenError ? (
                <p
                  data-testid="browser-fen-error"
                  className="text-xs text-rust"
                >
                  {fenError}
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-sand/70">
              <Badge label={moveLabel} />
              <Badge label={sanLabel} />
              <Badge label={clockLabel} />
            </div>
          </div>
        </div>
      )}
    </ModalShell>,
    document.body,
  );
}
