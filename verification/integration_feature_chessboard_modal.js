const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const { ensureCardExpanded } = require('./helpers/client_e2e_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';

const FEN_PATTERN =
  /([prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+)/;
const selectors = {
  row: '[data-testid^="positions-row-"]',
  modal: '[data-testid="chessboard-modal"]',
  board: '[data-testid="chessboard-modal-board"]',
  close: '[data-testid="chessboard-modal-close"]',
};

const extractFenFromRow = (text) => {
  const match = text.match(FEN_PATTERN);
  return match ? match[1] : null;
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await ensureCardExpanded(page, 'dashboard-card-positions-list');

    await page.waitForSelector(selectors.row, { timeout: 60000 });

    const fen = await page.evaluate((selector) => {
      const row = document.querySelector(selector);
      if (!row) return null;
      return row.textContent || '';
    }, selectors.row);

    const parsedFen = extractFenFromRow(fen);

    if (!parsedFen) {
      throw new Error('Failed to extract a FEN string from the positions row.');
    }

    await page.$eval(selectors.row, (row) => row.click());
    await new Promise((resolve) => setTimeout(resolve, 200));
    await page.waitForSelector(selectors.modal, { timeout: 60000 });
    await page.waitForSelector(selectors.board, { timeout: 60000 });

    const modalState = await page.evaluate(() => {
      const modal = document.querySelector('[data-testid="chessboard-modal"]');
      const boardContainer = document.querySelector(
        '[data-testid="chessboard-modal-board"]',
      );
      const fenNode = modal?.querySelector('p');
      const closeButton = modal?.querySelector(
        '[data-testid="chessboard-modal-close"]',
      );
      const boardHasTexture = Boolean(
        boardContainer &&
          Array.from(boardContainer.querySelectorAll('div')).some((node) =>
            (node instanceof HTMLElement
              ? node.style.backgroundImage
              : ''
            ).includes('listudy-board-texture'),
          ),
      );

      return {
        modalVisible: Boolean(modal),
        boardVisible: Boolean(boardContainer),
        closeVisible: Boolean(closeButton),
        modalText: modal?.textContent || '',
        fenText: fenNode?.textContent || '',
        boardHasTexture,
      };
    });

    if (
      !modalState.modalVisible ||
      !modalState.boardVisible ||
      !modalState.closeVisible
    ) {
      throw new Error('Chessboard modal did not render expected controls.');
    }

    if (!modalState.boardHasTexture) {
      throw new Error('Chessboard modal board did not render listudy styling.');
    }

    if (!modalState.modalText.includes(parsedFen)) {
      throw new Error('Chessboard modal did not include the expected FEN.');
    }

    await page.click(selectors.close);
    await page.waitForFunction(
      (modalSelector) => !document.querySelector(modalSelector),
      { timeout: 60000 },
      selectors.modal,
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
