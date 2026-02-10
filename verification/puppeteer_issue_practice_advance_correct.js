const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const {
  selectSource,
  ensurePracticeCardExpanded,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'issue-practice-advance-correct-2026-02-10.png';
const source = process.env.TACTIX_SOURCE || 'chesscom';

const selectors = {
  practiceStart: '[data-testid="practice-start"]',
  practiceModal: '[data-testid="chessboard-modal"]',
  practiceInput: '[data-testid="chessboard-modal"] input[placeholder*="UCI"]',
  practiceSummary: '[data-testid="practice-session-summary"]',
  practiceBestMove: '[data-testid="practice-best-move"]',
  practiceQueueRow: '[data-testid^="practice-queue-row-"]',
};

const UCI_PATTERN = /[a-h][1-8][a-h][1-8][qrbn]?/i;

function parseProgress(summaryText) {
  const match = summaryText.match(/(\d+)\s+of\s+(\d+)\s+attempts/i);
  if (!match) {
    throw new Error(`Unable to parse practice progress from: ${summaryText}`);
  }
  return { completed: Number(match[1]), total: Number(match[2]) };
}

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

async function getPracticeFenFromModal(page) {
  return page.evaluate((selector) => {
    const modal = document.querySelector(selector);
    if (!modal) return '';
    const fenRegex =
      /^[prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$/;
    const nodes = Array.from(modal.querySelectorAll('p'));
    const match = nodes
      .map((node) => node.textContent?.trim() || '')
      .find((text) => fenRegex.test(text));
    return match || '';
  }, selectors.practiceModal);
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await selectSource(page, source);
    await ensurePracticeCardExpanded(page);

    await page.waitForSelector(selectors.practiceQueueRow, { timeout: 60000 });
    const rowCount = await page.$$eval(
      selectors.practiceQueueRow,
      (rows) => rows.length,
    );
    if (rowCount < 2) {
      throw new Error(
        `Need at least 2 practice items to verify advance, found ${rowCount}.`,
      );
    }

    const bestMove = await getBestMoveFromQueue(page);
    if (!bestMove) {
      throw new Error('Unable to read a best move from the practice queue.');
    }

    await page.waitForSelector(selectors.practiceStart, { timeout: 60000 });
    await page.$eval(selectors.practiceStart, (button) => button.click());
    await page.waitForSelector(selectors.practiceModal, { timeout: 60000 });
    await page.waitForSelector(selectors.practiceInput, { timeout: 60000 });

    const beforeSummaryText = await page.$eval(
      selectors.practiceSummary,
      (el) => el.textContent || '',
    );
    const beforeSummary = parseProgress(beforeSummaryText);
    const beforeFen = await getPracticeFenFromModal(page);
    if (!beforeFen) {
      throw new Error('Practice FEN not found before submission.');
    }

    await page.click(selectors.practiceInput, { clickCount: 3 });
    await page.keyboard.type(bestMove);
    await page.keyboard.press('Enter');

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

    await page.waitForFunction(
      (modalSelector, bestMoveSelector, previousFen) => {
        const modal = document.querySelector(modalSelector);
        if (!modal) return false;
        const hasFeedback = Boolean(document.querySelector(bestMoveSelector));
        const fenRegex =
          /^[prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$/;
        const fen = Array.from(modal.querySelectorAll('p'))
          .map((node) => node.textContent?.trim() || '')
          .find((text) => fenRegex.test(text));
        return Boolean(fen && fen !== previousFen && hasFeedback);
      },
      { timeout: 60000 },
      selectors.practiceModal,
      selectors.practiceBestMove,
      beforeFen,
    );

    const afterSummaryText = await page.$eval(
      selectors.practiceSummary,
      (el) => el.textContent || '',
    );
    const afterSummary = parseProgress(afterSummaryText);
    if (afterSummary.completed !== beforeSummary.completed + 1) {
      throw new Error(
        `Expected completed to increment from ${beforeSummary.completed} to ${beforeSummary.completed + 1}, got ${afterSummary.completed}.`,
      );
    }
    if (afterSummary.total !== beforeSummary.total) {
      throw new Error(
        `Expected total to stay ${beforeSummary.total}, got ${afterSummary.total}.`,
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
