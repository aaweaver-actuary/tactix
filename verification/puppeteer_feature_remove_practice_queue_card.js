const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const { ensurePracticeCardExpanded } = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-remove-practice-queue-card-2026-02-10.png';

const selectors = {
  practiceQueueCard: '[data-testid="practice-queue-card"]',
  practiceButton: '[data-testid="practice-button"]',
  practiceModal: '[data-testid="chessboard-modal"]',
  practiceMoveInput: '[data-testid="chessboard-modal"] input[placeholder*="UCI"]',
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await ensurePracticeCardExpanded(page);

    const practiceQueueCard = await page.$(selectors.practiceQueueCard);
    if (practiceQueueCard) {
      throw new Error('Practice queue card should not render on the dashboard.');
    }

    await page.waitForSelector(selectors.practiceButton, { timeout: 60000 });
    const isDisabled = await page.$eval(
      selectors.practiceButton,
      (button) => button instanceof HTMLButtonElement && button.disabled,
    );

    if (!isDisabled) {
      await page.click(selectors.practiceButton);
      await page.waitForSelector(selectors.practiceModal, { timeout: 60000 });
      await page.waitForSelector(selectors.practiceMoveInput, { timeout: 60000 });
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
