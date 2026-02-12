import { Chess } from 'chess.js';

export default function formatPgnMoveList(pgn: string): string[] {
  if (!pgn) return [];
  const sanitized = pgn.trim();
  if (!sanitized) return [];
  const chess = new Chess();
  try {
    const loaded = chess.loadPgn(sanitized, { sloppy: true });
    if (loaded) {
      const history = chess.history();
      if (!history.length) return [];
      const lines: string[] = [];
      for (let i = 0; i < history.length; i += 2) {
        const moveNumber = Math.floor(i / 2) + 1;
        const white = history[i];
        const black = history[i + 1];
        lines.push(
          black
            ? `${moveNumber}. ${white} ${black}`
            : `${moveNumber}. ${white}`,
        );
      }
      return lines;
    }
  } catch {
    // Fall through to manual parsing.
  }

  const movetext = sanitized
    .replace(/\r/g, '')
    .replace(/\[[^\]]*\]\s*/g, '')
    .replace(/\{[^}]*\}/g, '')
    .replace(/\([^)]*\)/g, '')
    .replace(/\$\d+/g, '')
    .trim();
  if (!movetext || !/\d+\./.test(movetext)) return [];

  const tokens = movetext.split(/\s+/).filter((token) => {
    if (/^\d+\.{1,3}$/.test(token)) return false;
    if (/^(1-0|0-1|1\/2-1\/2|\*)$/.test(token)) return false;
    return true;
  });
  if (!tokens.length) return [];
  const lines: string[] = [];
  for (let i = 0; i < tokens.length; i += 2) {
    const moveNumber = Math.floor(i / 2) + 1;
    const white = tokens[i];
    const black = tokens[i + 1];
    lines.push(
      black ? `${moveNumber}. ${white} ${black}` : `${moveNumber}. ${white}`,
    );
  }
  return lines;
}
