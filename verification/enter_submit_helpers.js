const { Chess } = require('../client/node_modules/chess.js');

async function selectSource(page, source) {
  const targetSource = source || 'chesscom';
  const labelMap = {
    chesscom: 'Chess.com',
    lichess: 'Lichess',
    all: 'All',
  };
  const waitForDashboardSource = async () => {
    await page.waitForResponse((response) => {
      if (!response.url().includes('/api/dashboard')) return false;
      if (response.status() !== 200) return false;
      try {
        const url = new URL(response.url());
        const value = url.searchParams.get('source');
        if (targetSource === 'all') {
          return value === null;
        }
        return value === targetSource;
      } catch (err) {
        return false;
      }
    }, { timeout: 60000 });
  };
  const waitForPracticeQueueSource = async () => {
    await page.waitForResponse((response) => {
      if (!response.url().includes('/api/practice/queue')) return false;
      if (response.status() !== 200) return false;
      try {
        const url = new URL(response.url());
        const value = url.searchParams.get('source');
        if (targetSource === 'all') {
          return value === null;
        }
        return value === targetSource;
      } catch (err) {
        return false;
      }
    }, { timeout: 60000 });
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
    const currentValue = await page.$eval(
      'select[data-testid="filter-source"]',
      (el) => (el instanceof HTMLSelectElement ? el.value : ''),
    );
    if (currentValue === targetSource) {
      return;
    }
    const dashboardPromise = waitForDashboardSource();
    const practicePromise = waitForPracticeQueueSource();
    await page.select('select[data-testid="filter-source"]', targetSource);
    await page.waitForFunction(
      (value) => {
        const el = document.querySelector(
          'select[data-testid="filter-source"]',
        );
        return el && (el).value === value;
      },
      { timeout: 60000 },
      targetSource,
    );
    await Promise.all([dashboardPromise, practicePromise]);
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
    await waitForDashboardSource();
    await waitForPracticeQueueSource();
  }
}

async function getBestMoveFromPage(page) {
  const bestLabel = await page.$$eval('h3', (headers) => {
    const header = headers.find((node) =>
      (node.textContent || '').includes('Practice attempt'),
    );
    const card = header?.closest('.card');
    if (!card) return '';
    const spans = Array.from(card.querySelectorAll('span'));
    const best = spans.find((span) => {
      const text = span.textContent?.trim() || '';
      return text.startsWith('Best ') && text !== 'Best --';
    });
    return best?.textContent || '';
  });

  const rawBestMove = bestLabel.replace('Best ', '').trim();
  const uciPattern = /^[a-h][1-8][a-h][1-8][qrbn]?$/i;
  if (!rawBestMove || rawBestMove === '--' || !uciPattern.test(rawBestMove)) {
    return null;
  }
  return rawBestMove;
}

async function getFenFromPage(page) {
  const fen = await page.$$eval('h3', (headers) => {
    const fenRegex =
      /^[prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$/;
    const header = headers.find((node) =>
      (node.textContent || '').includes('Practice attempt'),
    );
    const card = header?.closest('.card');
    if (!card) return '';
    const nodes = Array.from(card.querySelectorAll('p'));
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
