const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const { ensureCardExpanded } = require('./helpers/client_e2e_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';

const FEN_PATTERN =
  /([prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+)/;

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await ensureCardExpanded(page, 'dashboard-card-positions-list');

    const rowSelector = '[data-testid^="positions-row-"]';
    await page.waitForSelector(rowSelector, { timeout: 60000 });

    const fen = await page.evaluate((selector, patternSource) => {
      const row = document.querySelector(selector);
      if (!row) return null;
      const pattern = new RegExp(patternSource);
      const match = row.textContent?.match(pattern);
      return match ? match[1] : null;
    }, rowSelector, FEN_PATTERN.source);

    if (!fen) {
      throw new Error('Failed to extract a FEN string from the positions row.');
    }

    await page.click(rowSelector, { delay: 25 });
    await new Promise((resolve) => setTimeout(resolve, 200));
    await page.waitForSelector('[data-testid="chessboard-modal"]', {
      timeout: 60000,
    });
    await page.waitForSelector('[data-testid="chessboard-modal-board"]', {
      timeout: 60000,
    });

    const modalState = await page.evaluate(() => {
      const modal = document.querySelector('[data-testid="chessboard-modal"]');
      const board = document.querySelector(
        '[data-testid="chessboard-modal-board"]',
      );
      const fenNode = modal?.querySelector('p');
      const closeButton = modal?.querySelector(
        '[data-testid="chessboard-modal-close"]',
      );
      return {
        modalVisible: Boolean(modal),
        boardVisible: Boolean(board),
        closeVisible: Boolean(closeButton),
        modalText: modal?.textContent || '',
        fenText: fenNode?.textContent || '',
      };
    });

    if (
      !modalState.modalVisible ||
      !modalState.boardVisible ||
      !modalState.closeVisible
    ) {
      throw new Error('Chessboard modal did not render expected controls.');
    }

    if (!modalState.modalText.includes(fen)) {
      throw new Error('Chessboard modal did not include the expected FEN.');
    }

    await page.click('[data-testid="chessboard-modal-close"]');
    await page.waitForFunction(
      () => !document.querySelector('[data-testid="chessboard-modal"]'),
      { timeout: 60000 },
    );

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Chessboard modal integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
