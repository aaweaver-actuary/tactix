const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const { clickButtonByText } = require('./helpers/button_helpers');
const {
  selectSource,
  ensurePracticeCardExpanded,
  waitForPracticeReady,
  getFenFromPage,
  buildFallbackMove,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'chesscom';

const selectors = {
  practiceAttemptCard: '[data-testid="dashboard-card-practice-attempt"]',
  practiceButton: '[data-testid="practice-button"]',
  practiceModal: '[data-testid="chessboard-modal"]',
  practiceMoveInput: '[data-testid="chessboard-modal"] input[placeholder*="UCI"]',
  practiceBestMove: '[data-testid="practice-best-move"]',
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

    const hasPracticeCard = await page.evaluate((sel) => {
      return Boolean(document.querySelector(sel.practiceAttemptCard));
    }, selectors);

    if (hasPracticeCard) {
      throw new Error('Practice attempt card should not render on the dashboard.');
    }

    await page.waitForSelector(selectors.practiceButton, { timeout: 60000 });
    await clickButtonByText(page, 'Refresh metrics');
    try {
      await waitForPracticeReady(page, selectors.practiceButton, 20000);
    } catch (err) {
      await clickButtonByText(page, 'Run + Refresh');
      await waitForPracticeReady(page, selectors.practiceButton, 60000);
    }

    await page.click(selectors.practiceButton);
    await page.waitForSelector(selectors.practiceModal, { timeout: 60000 });
    await page.waitForSelector(selectors.practiceMoveInput, { timeout: 60000 });

    const fen = await getFenFromPage(page);
    const attemptMove = buildFallbackMove(fen);

    await page.click(selectors.practiceMoveInput, { clickCount: 3 });
    await page.keyboard.type(attemptMove);
    await clickButtonByText(page, 'Submit attempt');

    await page.waitForSelector(selectors.practiceBestMove, { timeout: 60000 });

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Practice attempt card removal integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
