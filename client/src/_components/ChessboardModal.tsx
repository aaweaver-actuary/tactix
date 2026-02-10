import type { CSSProperties, RefObject } from 'react';
import { createPortal } from 'react-dom';
import type {
  DashboardPayload,
  PracticeAttemptResponse,
  PracticeQueueItem,
} from '../api';
import BaseChessboard from './BaseChessboard';
import Badge from './Badge';
import BaseButton from './BaseButton';
import ChessboardPanel from './ChessboardPanel';
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

export default function ChessboardModal({
  open,
  position,
  practice,
  onClose,
}: ChessboardModalProps) {
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
            <BaseButton
              className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
              onClick={onClose}
              data-testid="chessboard-modal-close"
            >
              Close
            </BaseButton>
          }
        />
        <div className="mt-4">
          <PracticeModalContent {...practice} />
        </div>
      </ModalShell>,
      document.body,
    );
  }

  const fen = position?.fen ?? '';
  const orientation = getOrientation(position?.fen ?? null);
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
          <BaseButton
            className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
            onClick={onClose}
            data-testid="chessboard-modal-close"
          >
            Close
          </BaseButton>
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
