const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture, captureScreenshot } = require('./helpers/puppeteer_capture');
const {
  selectSource,
  getFenFromPage,
  ensurePracticeCardExpanded,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'chesscom';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-practice-orientation-2026-02-10.png';

const selectors = {
  practiceStart: '[data-testid="practice-start"]',
  practiceModal: '[data-testid="chessboard-modal"]',
  board: '[data-boardid="practice-board"]',
};

const getExpectedBottomLeft = (fen) => {
  const side = fen?.split(' ')[1];
  return side === 'b' ? 'h8' : 'a1';
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await selectSource(page, source);
    await ensurePracticeCardExpanded(page);

    await page.waitForSelector(selectors.practiceStart, { timeout: 60000 });
    await page.click(selectors.practiceStart);
    await page.waitForSelector(selectors.practiceModal, { timeout: 60000 });
    await page.waitForSelector(`${selectors.board} [data-square]`, {
      timeout: 60000,
    });

    const fen = await getFenFromPage(page);
    const expectedBottomLeft = getExpectedBottomLeft(fen);

    const bottomLeftSquare = await page.evaluate((boardSelector) => {
      const squares = Array.from(
        document.querySelectorAll(`${boardSelector} [data-square]`),
      );
      if (!squares.length) return null;
      const entries = squares.map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          square: el.getAttribute('data-square'),
          left: rect.left,
          bottom: rect.bottom,
        };
      });
      const maxBottom = Math.max(...entries.map((entry) => entry.bottom));
      const bottomRow = entries.filter(
        (entry) => Math.abs(entry.bottom - maxBottom) < 1,
      );
      bottomRow.sort((a, b) => a.left - b.left);
      return bottomRow[0]?.square || null;
    }, selectors.board);

    if (!bottomLeftSquare) {
      throw new Error('Unable to determine bottom-left square for practice board.');
    }

    if (bottomLeftSquare !== expectedBottomLeft) {
      throw new Error(
        `Expected bottom-left square ${expectedBottomLeft} but found ${bottomLeftSquare}.`,
      );
    }

    const outPath = await captureScreenshot(
      page,
      path.resolve(__dirname),
      screenshotName,
    );
    console.log('Saved screenshot to', outPath);

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
