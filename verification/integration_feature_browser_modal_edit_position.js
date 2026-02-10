const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const { ensureCardExpanded } = require('./helpers/client_e2e_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';

const selectors = {
  row: '[data-testid^="positions-row-"]',
  modal: '[data-testid="chessboard-modal"]',
  input: '[data-testid="browser-fen-input"]',
  apply: '[data-testid="browser-fen-apply"]',
  error: '[data-testid="browser-fen-error"]',
};

const validFen = '8/8/8/8/8/8/4K3/7k w - - 0 1';

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

    await setInputValue(page, selectors.input, 'not a fen');
    await page.click(selectors.apply);
    await page.waitForSelector(selectors.error, { timeout: 60000 });

    await setInputValue(page, selectors.input, validFen);
    await page.click(selectors.apply);
    await page.waitForFunction(
      (modalSelector, expectedFen) => {
        const modal = document.querySelector(modalSelector);
        return modal?.textContent?.includes(expectedFen);
      },
      { timeout: 60000 },
      selectors.modal,
      validFen,
    );

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Browser modal edit integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
