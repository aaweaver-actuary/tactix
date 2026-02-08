import { Chess } from 'chess.js';

type LichessAnalysisOptions = {
  anchorPly?: number | null;
};

const LICHESS_ANALYSIS_BASE = 'https://lichess.org/analysis/pgn';

const toColorParam = (turn: 'w' | 'b') => (turn === 'w' ? 'white' : 'black');

const encodeMove = (move: string) => encodeURIComponent(move);

export default function buildLichessAnalysisUrl(
  pgn: string | null | undefined,
  options: LichessAnalysisOptions = {},
): string | null {
  if (!pgn) return null;
  const sanitized = pgn.trim();
  if (!sanitized) return null;
  const chess = new Chess();
  try {
    chess.loadPgn(sanitized, { sloppy: true });
  } catch {
    return null;
  }

  const history = chess.history();
  if (!history.length) return null;

  const movePath = history.map(encodeMove).join('_');
  const colorParam = toColorParam(chess.turn());
  const anchorPly =
    options.anchorPly !== undefined && options.anchorPly !== null
      ? Math.max(0, Math.floor(options.anchorPly))
      : history.length;
  const anchor = anchorPly > 0 ? `#${anchorPly}` : '';

  return `${LICHESS_ANALYSIS_BASE}/${movePath}?color=${colorParam}${anchor}`;
}
