const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const { ensureCardExpanded } = require('./helpers/client_e2e_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-opp-hanging-piece-illegal-capture-2026-02-12.png';

const selectors = {
  row: '[data-testid^="positions-row-"]',
  modal: '[data-testid="chessboard-modal"]',
  input: '[data-testid="browser-fen-input"]',
  apply: '[data-testid="browser-fen-apply"]',
  close: '[data-testid="chessboard-modal-close"]',
};

const pinnedFen = '4r1k1/8/8/8/5q2/8/4N3/4K3 w - - 0 1';

const setInputValue = async (page, selector, value) => {
  await page.click(selector, { clickCount: 3 });
  await page.keyboard.press('Backspace');
  await page.type(selector, value);
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await ensureCardExpanded(page, 'dashboard-card-positions-list');

    await page.waitForSelector(selectors.row, { timeout: 60000 });
    await page.$eval(selectors.row, (row) => row.click());

    await page.waitForSelector(selectors.modal, { timeout: 60000 });
    await page.waitForSelector(selectors.input, { timeout: 60000 });

    await setInputValue(page, selectors.input, pinnedFen);
    await page.click(selectors.apply);
    await page.waitForFunction(
      (modalSelector, expectedFen) => {
        const modal = document.querySelector(modalSelector);
        return modal?.textContent?.includes(expectedFen);
      },
      { timeout: 60000 },
      selectors.modal,
      pinnedFen,
    );

    const outPath = await captureScreenshot(
      page,
      path.resolve(__dirname),
      screenshotName,
    );
    console.log('Saved screenshot to', outPath);

    await page.click(selectors.close);

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
