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

    const rowSelector = '[data-testid^="positions-row-"]';
    await page.waitForSelector(rowSelector, { timeout: 60000 });
    const rowTag = await page.$eval(rowSelector, (row) => row.tagName);
    console.log(`Found positions row tag: ${rowTag}`);
    const rowText = await page.$eval(rowSelector, (row) => row.innerText);
    const fenMatch = rowText.match(FEN_PATTERN);
    if (!fenMatch) {
      throw new Error(`Unable to read FEN from positions row: ${rowText}`);
    }
    const fen = fenMatch[1];

    await page.click(rowSelector, { delay: 25 });
    await page.waitForSelector('[data-testid="chessboard-modal"]', {
      timeout: 60000,
    });
    await page.waitForSelector('[data-testid="chessboard-modal-board"]', {
      timeout: 60000,
    });

    const modalText = await page.$eval(
      '[data-testid="chessboard-modal"]',
      (modal) => modal.innerText,
    );
    if (!modalText.includes(fen)) {
      throw new Error('Chessboard modal does not show the expected FEN.');
    }

    const outDir = path.resolve(__dirname);
    const openPath = await captureScreenshot(page, outDir, SCREENSHOT_OPEN);
    console.log('Saved screenshot to', openPath);

    await page.click('[data-testid="chessboard-modal-close"]');
    await page.waitForFunction(
      () => !document.querySelector('[data-testid="chessboard-modal"]'),
      { timeout: 60000 },
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
