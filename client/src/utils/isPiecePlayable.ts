import { Chess, Square } from 'chess.js';
import { PracticeQueueItem } from '../api';

type DraggablePiece = string | { color: string; type: string };

interface DraggablePieceDetails {
  piece: DraggablePiece;
  sourceSquare: Square;
}

export default function isPiecePlayable(
  practiceFen: string,
  currentPractice: PracticeQueueItem,
): ({ piece }: DraggablePieceDetails) => boolean {
  return ({ piece }: DraggablePieceDetails) => {
    const fen = practiceFen || currentPractice.fen;
    if (!fen) return false;
    const board = new Chess(fen);
    const turn = board.turn();
    const color = typeof piece === 'string' ? piece[0] : piece.color;
    return turn === color;
  };
}
