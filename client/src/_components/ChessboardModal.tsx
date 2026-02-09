import { createPortal } from 'react-dom';
import type { DashboardPayload } from '../api';
import {
  listudyBoardStyle,
  listudyDarkSquareStyle,
  listudyLightSquareStyle,
  listudyNotationStyle,
  listudyPieces,
} from '../utils/listudyAssets';
import Badge from './Badge';
import Chessboard from './Chessboard';
import Text from './Text';

type PositionEntry = DashboardPayload['positions'][number];

interface ChessboardModalProps {
  open: boolean;
  position: PositionEntry | null;
  onClose: () => void;
}

const getOrientation = (fen: string | null) => {
  const side = fen?.split(' ')[1];
  return side === 'b' ? 'black' : 'white';
};

export default function ChessboardModal({
  open,
  position,
  onClose,
}: ChessboardModalProps) {
  if (!open) {
    return null;
  }

  const fen = position?.fen ?? '';
  const orientation = getOrientation(position?.fen ?? null);

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 py-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      data-testid="chessboard-modal"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-white/10 bg-slate-950/95 p-5 shadow-2xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Text mode="uppercase" value="Position board" />
            <div className="text-xs text-sand/60">
              Review the selected position in context
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-white/10 px-3 py-1 text-xs text-sand/70 hover:border-white/30"
            aria-label="Close chessboard"
            data-testid="chessboard-modal-close"
          >
            Close
          </button>
        </div>

        {!position ? (
          <div className="mt-4 text-sm text-sand/70">
            Select a position to view the board.
          </div>
        ) : (
          <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-[360px_1fr]">
            <div
              className="rounded-lg border border-white/10 bg-white/5 p-3"
              data-testid="chessboard-modal-board"
            >
              <Chessboard
                id="chessboard-modal-board"
                position={fen}
                boardOrientation={orientation}
                boardWidth={340}
                showBoardNotation
                customNotationStyle={listudyNotationStyle}
                customBoardStyle={listudyBoardStyle}
                customLightSquareStyle={listudyLightSquareStyle}
                customDarkSquareStyle={listudyDarkSquareStyle}
                customPieces={listudyPieces}
              />
            </div>
            <div className="space-y-4">
              <div>
                <Text value="FEN" />
                <Text value={fen || '--'} mode="monospace" size="xs" />
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-sand/70">
                <Badge label={`Move ${position.move_number ?? '--'}`} />
                <Badge
                  label={position.san ? `SAN ${position.san}` : 'SAN --'}
                />
                <Badge label={`${position.clock_seconds ?? '--'}s`} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
