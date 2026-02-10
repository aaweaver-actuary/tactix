const puppeteer = require('../client/node_modules/puppeteer');
const { Chess } = require('../client/node_modules/chess.js');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const {
  selectSource,
  getFenFromPage,
  ensurePracticeCardExpanded,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'chesscom';

const selectors = {
  practiceStart: '[data-testid="practice-start"]',
  practiceModal: '[data-testid="chessboard-modal"]',
  practiceInput: '[data-testid="chessboard-modal"] input[placeholder*="UCI"]',
  bestMoveBadge: '[data-testid="practice-best-move"]',
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await selectSource(page, source);
    await ensurePracticeCardExpanded(page);

    await page.waitForSelector(selectors.practiceStart, { timeout: 60000 });
    await page.click(selectors.practiceStart);
    await page.waitForSelector(selectors.practiceModal, { timeout: 60000 });
    await page.waitForSelector(selectors.practiceInput, { timeout: 60000 });

    const hasBestBadge = await page.$(selectors.bestMoveBadge);
    if (hasBestBadge) {
      throw new Error('Best move badge should be hidden before attempting.');
    }

    const fen = await getFenFromPage(page);
    const board = new Chess(fen);
    const attemptMove = board
      .moves({ verbose: true })
      .map((move) => `${move.from}${move.to}${move.promotion || ''}`)
      .find(Boolean);
    if (!attemptMove) {
      throw new Error('Unable to find a legal move for practice attempt.');
    }

    await page.click(selectors.practiceInput, { clickCount: 3 });
    await page.keyboard.type(attemptMove);
    await page.$$eval('button', (buttons) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes('Submit attempt'),
      );
      if (target) target.click();
    });

    await page.waitForSelector(selectors.bestMoveBadge, { timeout: 60000 });

    const badgeText = await page.$eval(
      selectors.bestMoveBadge,
      (node) => node.textContent || '',
    );
    if (!badgeText.includes('Best')) {
      throw new Error('Expected best move badge to appear after attempt.');
    }

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Practice best move visibility integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
