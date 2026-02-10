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
  practiceInput: '[data-testid="chessboard-modal"] input[placeholder*="UCI"]',
  practiceQueueRow: '[data-testid^="practice-queue-row-"]',
  board: '[data-boardid="practice-board"]',
};

const getExpectedBottomLeft = (fen) => {
  const side = fen?.split(' ')[1];
  return side === 'b' ? 'h8' : 'a1';
};

const UCI_PATTERN = /[a-h][1-8][a-h][1-8][qrbn]?/i;

async function getBestMoveFromQueue(page) {
  const bestText = await page.evaluate((rowSelector) => {
    const row = document.querySelector(rowSelector);
    if (!row) return null;
    const cells = Array.from(row.querySelectorAll('td')).map(
      (cell) => cell.textContent?.trim() || '',
    );
    return cells[2] || null;
  }, selectors.practiceQueueRow);

  if (!bestText) return null;
  const match = bestText.match(UCI_PATTERN);
  return match ? match[0] : null;
}

async function getBottomLeftSquare(page) {
  return page.evaluate((boardSelector) => {
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
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await selectSource(page, source);
    await ensurePracticeCardExpanded(page);
    console.log('Practice card ready.');

    await page.waitForSelector(selectors.practiceQueueRow, { timeout: 60000 });
    const rowCount = await page.$$eval(
      selectors.practiceQueueRow,
      (rows) => rows.length,
    );
    if (rowCount < 2) {
      throw new Error(
        `Need at least 2 practice items to verify orientation advance, found ${rowCount}.`,
      );
    }

    const bestMove = await getBestMoveFromQueue(page);
    if (!bestMove) {
      throw new Error('Unable to read a best move from the practice queue.');
    }
    console.log('Best move loaded from queue:', bestMove);

    await page.waitForSelector(selectors.practiceStart, { timeout: 60000 });
    await page.click(selectors.practiceStart);
    await page.waitForSelector(selectors.practiceModal, { timeout: 60000 });
    await page.waitForSelector(selectors.practiceInput, { timeout: 60000 });
    await page.waitForSelector(`${selectors.board} [data-square]`, {
      timeout: 60000,
    });
    console.log('Practice modal ready.');

    const fen = await getFenFromPage(page);
    const expectedBottomLeft = getExpectedBottomLeft(fen);
    console.log('Initial FEN', fen);

    const bottomLeftSquare = await getBottomLeftSquare(page);

    if (!bottomLeftSquare) {
      throw new Error('Unable to determine bottom-left square for practice board.');
    }

    if (bottomLeftSquare !== expectedBottomLeft) {
      throw new Error(
        `Expected bottom-left square ${expectedBottomLeft} but found ${bottomLeftSquare}.`,
      );
    }

    await page.click(selectors.practiceInput, { clickCount: 3 });
    await page.keyboard.type(bestMove);
    await page.keyboard.press('Enter');
    console.log('Submitted correct move.');

    await page.waitForFunction(
      (selector) => {
        const modal = document.querySelector(selector);
        if (!modal) return false;
        return Array.from(modal.querySelectorAll('span')).some((el) =>
          (el.textContent || '').includes('Correct'),
        );
      },
      { timeout: 60000 },
      selectors.practiceModal,
    );

    const moveFenHandle = await page.waitForFunction(
      (modalSelector, previousFen) => {
        const modal = document.querySelector(modalSelector);
        if (!modal) return null;
        const fenRegex =
          /^[prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$/;
        const fen = Array.from(modal.querySelectorAll('p'))
          .map((node) => node.textContent?.trim() || '')
          .find((text) => fenRegex.test(text));
        if (!fen || fen === previousFen) return null;
        return fen;
      },
      { timeout: 60000 },
      selectors.practiceModal,
      fen,
    );
    const moveFen = await moveFenHandle.jsonValue();
    console.log('Move FEN', moveFen);

    const feedbackBottomLeft = await getBottomLeftSquare(page);
    if (!feedbackBottomLeft) {
      throw new Error('Unable to read bottom-left square after feedback.');
    }
    if (feedbackBottomLeft !== expectedBottomLeft) {
      throw new Error(
        `Expected feedback orientation ${expectedBottomLeft} but found ${feedbackBottomLeft}.`,
      );
    }

    await new Promise((resolve) => setTimeout(resolve, 500));
    const highlightCount = await page.evaluate((boardSelector) => {
      const squares = Array.from(
        document.querySelectorAll(`${boardSelector} [data-square]`),
      );
      const highlighted = squares.filter((square) => {
        const inline = square.getAttribute('style') || '';
        const color = window.getComputedStyle(square).backgroundColor || '';
        return inline.includes('background') || color.includes('14, 116, 144');
      });
      return highlighted.length;
    }, selectors.board);

    if (highlightCount < 2) {
      throw new Error(
        `Expected at least 2 highlighted squares, found ${highlightCount}.`,
      );
    }
    console.log('Move highlights present.');

    const expectedAfterMove = getExpectedBottomLeft(moveFen);
    if (expectedAfterMove !== expectedBottomLeft) {
      throw new Error(
        `Expected orientation to stay ${expectedBottomLeft} during feedback, but move FEN implies ${expectedAfterMove}.`,
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
