const { Chess } = require('../client/node_modules/chess.js');
const {
  closeFiltersModal,
  openFiltersModal,
} = require('./helpers/filters_modal_helpers');

const SOURCE_LABELS = {
  chesscom: 'Chess.com',
  lichess: 'Lichess',
  all: 'All',
};

async function waitForSourceResponse(page, targetSource, endpoint) {
  await page.waitForResponse((response) => {
    if (!response.url().includes(endpoint)) return false;
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
}

async function selectSource(page, source) {
  const targetSource = source || 'chesscom';
  try {
    await openFiltersModal(page);
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
      await closeFiltersModal(page);
      return;
    }
    const dashboardPromise = waitForSourceResponse(
      page,
      targetSource,
      '/api/dashboard',
    );
    const practicePromise = waitForSourceResponse(
      page,
      targetSource,
      '/api/practice/queue',
    );
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
    await closeFiltersModal(page);
  } catch (err) {
    const label = SOURCE_LABELS[targetSource] || targetSource;
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
    await waitForSourceResponse(page, targetSource, '/api/dashboard');
    await waitForSourceResponse(page, targetSource, '/api/practice/queue');
    await closeFiltersModal(page);
  }
}

const ensureFiltersModalOpen = (page) => openFiltersModal(page);

async function getBestMoveFromPage(page) {
  const bestLabel = await page.evaluate(() => {
    const modal = document.querySelector('[data-testid="chessboard-modal"]');
    const scope = modal || document.body;
    const spans = Array.from(scope.querySelectorAll('span'));
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
    const modal = document.querySelector('[data-testid="chessboard-modal"]');
    const scope = modal || document.body;
    const nodes = Array.from(scope.querySelectorAll('p'));
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

async function ensurePracticeCardExpanded(page) {
  const practiceButton = '[data-testid="practice-button"]';
  await page.waitForSelector(practiceButton, { timeout: 60000 });
  await page.waitForFunction(
    (selector) => {
      const button = document.querySelector(selector);
      return button instanceof HTMLButtonElement;
    },
    { timeout: 60000 },
    practiceButton,
  );
}

async function waitForPracticeReady(page, selector, timeoutMs) {
  await page.waitForFunction(
    (selector) => {
      const button = document.querySelector(selector);
      return button instanceof HTMLButtonElement && !button.disabled;
    },
    { timeout: timeoutMs },
    selector,
  );
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
  ensureFiltersModalOpen,
  closeFiltersModal,
  ensurePracticeCardExpanded,
  waitForPracticeReady,
};
