const { Chess } = require('../client/node_modules/chess.js');

async function selectSource(page, source) {
  const targetSource = source || 'chesscom';
  const labelMap = {
    chesscom: 'Chess.com',
    lichess: 'Lichess',
    all: 'All',
  };
  try {
    await page.waitForFunction(
      () => {
        const el = document.querySelector(
          'select[data-testid="filter-source"]',
        );
        return el && !el.disabled;
      },
      { timeout: 60000 },
    );
    await page.select('select[data-testid="filter-source"]', targetSource);
  } catch (err) {
    const label = labelMap[targetSource] || targetSource;
    await page.$$eval(
      'button',
      (buttons, label) => {
        const target = buttons.find(
          (btn) => btn.textContent && btn.textContent.includes(label),
        );
        if (target) target.click();
      },
      label,
    );
  }
}

async function getBestMoveFromPage(page) {
  const bestLabel = await page.$$eval('span', (spans) => {
    const best = spans.find((span) => {
      const text = span.textContent?.trim() || '';
      return text.startsWith('Best ') && text !== 'Best --';
    });
    return best?.textContent || '';
  });

  const rawBestMove = bestLabel.replace('Best ', '').trim();
  if (!rawBestMove || rawBestMove === '--') {
    return null;
  }
  return rawBestMove;
}

async function getFenFromPage(page) {
  const fen = await page.$$eval('p', (nodes) => {
    const fenRegex =
      /^[prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$/;
    const match = nodes
      .map((node) => node.textContent?.trim() || '')
      .find((text) => fenRegex.test(text));
    return match || '';
  });
  if (!fen) {
    throw new Error('Practice FEN not found for fallback move.');
  }
  return fen;
}

function buildFallbackMove(fen) {
  const board = new Chess(fen);
  const moves = board.moves({ verbose: true });
  if (!moves.length) {
    throw new Error('No legal moves available for fallback.');
  }
  const move = moves[0];
  return `${move.from}${move.to}${move.promotion || ''}`;
}

module.exports = {
  selectSource,
  getBestMoveFromPage,
  getFenFromPage,
  buildFallbackMove,
};
