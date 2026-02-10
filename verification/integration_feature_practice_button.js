const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const {
  selectSource,
  ensurePracticeCardExpanded,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'chesscom';

const selectors = {
  hero: '[data-testid="dashboard-hero"]',
  practiceButton: '[data-testid="practice-button"]',
  practiceQueueRow: '[data-testid^="practice-queue-row-"]',
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
    await selectSource(page, source);
    await ensurePracticeCardExpanded(page);

    await page.waitForSelector(selectors.practiceButton, { timeout: 60000 });

    const buttonInHero = await page.$eval(
      selectors.hero,
      (hero, buttonSelector) => Boolean(hero.querySelector(buttonSelector)),
      selectors.practiceButton,
    );

    if (!buttonInHero) {
      throw new Error('Practice button should be rendered in the hero header.');
    }

    const hasQueueRows = await page.$$eval(
      selectors.practiceQueueRow,
      (rows) => rows.length > 0,
    );

    const isDisabled = await page.$eval(
      selectors.practiceButton,
      (button) => button instanceof HTMLButtonElement && button.disabled,
    );

    if (hasQueueRows) {
      if (isDisabled) {
        throw new Error('Practice button should be enabled when queue items exist.');
      }
      await page.click(selectors.practiceButton);
      await page.waitForSelector(selectors.practiceModal, { timeout: 60000 });
      await page.waitForSelector(selectors.practiceMoveInput, { timeout: 60000 });
    } else if (!isDisabled) {
      throw new Error('Practice button should be disabled when no queue items exist.');
    }

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Practice button integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
