const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const { ensureCardExpanded } = require('./helpers/client_e2e_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_OPEN =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-chessboard-modal-open-2026-02-09.png';
const SCREENSHOT_CLOSED = 'feature-chessboard-modal-closed-2026-02-09.png';

const FEN_PATTERN =
  /([prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+)/;
const selectors = {
  row: '[data-testid^="positions-row-"]',
  modal: '[data-testid="chessboard-modal"]',
  board: '[data-testid="chessboard-modal-board"]',
  close: '[data-testid="chessboard-modal-close"]',
};

const extractFen = (text) => {
  const match = text.match(FEN_PATTERN);
  return match ? match[1] : null;
};

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });

    await ensureCardExpanded(page, 'dashboard-card-positions-list');
    const cardState = await page.$eval(
      '[data-testid="dashboard-card-positions-list"] [data-state]',
      (node) => node.getAttribute('data-state'),
    );
    console.log(`Positions card state: ${cardState}`);

    await page.waitForSelector(selectors.row, { timeout: 60000 });
    const rowTag = await page.$eval(selectors.row, (row) => row.tagName);
    console.log(`Found positions row tag: ${rowTag}`);
    const rowText = await page.$eval(selectors.row, (row) => row.innerText);
    const fen = extractFen(rowText);
    if (!fen) {
      throw new Error(`Unable to read FEN from positions row: ${rowText}`);
    }

    await page.$eval(selectors.row, (row) => row.click());
    await page.waitForSelector(selectors.modal, { timeout: 60000 });
    await page.waitForSelector(selectors.board, { timeout: 60000 });

    const modalText = await page.$eval(
      selectors.modal,
      (modal) => modal.innerText,
    );
    if (!modalText.includes(fen)) {
      throw new Error('Chessboard modal does not show the expected FEN.');
    }

    const outDir = path.resolve(__dirname);
    const openPath = await captureScreenshot(page, outDir, SCREENSHOT_OPEN);
    console.log('Saved screenshot to', openPath);

    await page.click(selectors.close);
    await page.waitForFunction(
      (modalSelector) => !document.querySelector(modalSelector),
      { timeout: 60000 },
      selectors.modal,
    );

    const closedPath = await captureScreenshot(
      page,
      outDir,
      SCREENSHOT_CLOSED,
    );
    console.log('Saved screenshot to', closedPath);

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
