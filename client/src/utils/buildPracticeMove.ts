import { Chess, Square } from 'chess.js';

type ParsedUciMove = {
  from: Square;
  to: Square;
  promotion?: string;
};

type PracticeMoveResult = {
  uci: string;
  nextFen: string;
  from: Square;
  to: Square;
};

const parseUciMove = (rawMove: string): ParsedUciMove | null => {
  const trimmed = rawMove.trim().toLowerCase();
  if (trimmed.length < 4) return null;
  const from = trimmed.slice(0, 2) as Square;
  const to = trimmed.slice(2, 4) as Square;
  return { from, to, promotion: trimmed[4] };
};

const resolvePromotion = (
  board: Chess,
  from: Square,
  to: Square,
  promotion?: string,
): string | undefined => {
  if (promotion) return promotion;
  const piece = board.get(from);
  if (piece?.type !== 'p') return undefined;
  if (!to.endsWith('8') && !to.endsWith('1')) return undefined;
  return 'q';
};

const attemptBoardMove = (
  board: Chess,
  from: Square,
  to: Square,
  promotion?: string,
) => {
  try {
    return board.move({ from, to, promotion });
  } catch (err) {
    console.warn('Invalid move attempt', err);
    return null;
  }
};

const buildMoveResult = (
  board: Chess,
  from: Square,
  to: Square,
  promotion?: string,
): PracticeMoveResult => ({
  uci: `${from}${to}${promotion ?? ''}`,
  nextFen: board.fen(),
  from,
  to,
});

const buildPracticeMove = (
  fen: string,
  rawMove: string,
): PracticeMoveResult | null => {
  const parsed = parseUciMove(rawMove);
  if (!parsed) return null;
  const board = new Chess(fen);
  const promotion = resolvePromotion(
    board,
    parsed.from,
    parsed.to,
    parsed.promotion,
  );
  const move = attemptBoardMove(board, parsed.from, parsed.to, promotion);
  if (!move) return null;
  return buildMoveResult(board, parsed.from, parsed.to, promotion);
};

export default buildPracticeMove;
