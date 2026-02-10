const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const {
  selectSource,
  ensurePracticeCardExpanded,
  waitForPracticeReady,
  getFenFromPage,
  buildFallbackMove,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'chesscom';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-remove-practice-attempt-card-2026-02-10.png';

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

    const practiceCard = await page.$(selectors.practiceAttemptCard);
    if (practiceCard) {
      throw new Error('Practice attempt card should not render on the dashboard.');
    }

    await page.waitForSelector(selectors.practiceButton, { timeout: 60000 });
    await page.$$eval('button', (buttons) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes('Refresh metrics'),
      );
      if (target) target.click();
    });
    try {
      await waitForPracticeReady(page, selectors.practiceButton, 30000);
    } catch (err) {
      await page.$$eval('button', (buttons) => {
        const target = buttons.find(
          (btn) => btn.textContent && btn.textContent.includes('Run + Refresh'),
        );
        if (target) target.click();
      });
      await waitForPracticeReady(page, selectors.practiceButton, 120000);
    }

    await page.click(selectors.practiceButton);
    await page.waitForSelector(selectors.practiceModal, { timeout: 60000 });
    await page.waitForSelector(selectors.practiceMoveInput, { timeout: 60000 });

    const fen = await getFenFromPage(page);
    const attemptMove = buildFallbackMove(fen);

    await page.click(selectors.practiceMoveInput, { clickCount: 3 });
    await page.keyboard.type(attemptMove);
    await page.$$eval('button', (buttons) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes('Submit attempt'),
      );
      if (target) target.click();
    });

    await page.waitForFunction(
      (modalSelector) => {
        const modal = document.querySelector(modalSelector);
        if (!modal) return false;
        return Array.from(modal.querySelectorAll('span')).some((el) =>
          ['Correct', 'Missed'].some((label) => el.textContent?.includes(label)),
        );
      },
      { timeout: 60000 },
      selectors.practiceModal,
    );

    await page.waitForSelector(selectors.practiceBestMove, { timeout: 60000 });

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
