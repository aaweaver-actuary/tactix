import { Chess } from 'chess.js';

type LichessAnalysisOptions = {
  anchorPly?: number | null;
};

const LICHESS_ANALYSIS_BASE = 'https://lichess.org/analysis/pgn';

const toColorParam = (turn: 'w' | 'b') => (turn === 'w' ? 'white' : 'black');

const encodeMove = (move: string) => encodeURIComponent(move);

const normalizeAnchorPly = (
  anchorPly: number | null | undefined,
  fallback: number,
) => {
  if (anchorPly === null || anchorPly === undefined) return fallback;
  return Math.max(0, Math.floor(anchorPly));
};

const tryLoadPgn = (chess: Chess, pgn: string) => {
  try {
    chess.loadPgn(pgn, { strict: false });
    return chess.history().length > 0;
  } catch {
    return false;
  }
};

export default function buildLichessAnalysisUrl(
  pgn: string | null | undefined,
  options: LichessAnalysisOptions = {},
): string | null {
  const sanitized = pgn?.trim();
  if (!sanitized) return null;
  const chess = new Chess();
  if (!tryLoadPgn(chess, sanitized)) return null;

  const history = chess.history();
  if (!history.length) return null;

  const movePath = history.map(encodeMove).join('_');
  const colorParam = toColorParam(chess.turn());
  const anchorPly = normalizeAnchorPly(options.anchorPly, history.length);
  const anchor = anchorPly ? `#${anchorPly}` : '';

  return `${LICHESS_ANALYSIS_BASE}/${movePath}?color=${colorParam}${anchor}`;
}
