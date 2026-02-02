const puppeteer = require('puppeteer');
const path = require('path');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-021-chesscom-pagination.png';

async function clickButtonByText(page, text) {
  if (typeof page.locator === 'function') {
    const button = page.locator('button', { hasText: text });
    await button.click();
    return;
  }
  throw new Error('Puppeteer locator API is unavailable.');
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  await page.goto(targetUrl, { waitUntil: 'networkidle0' });
  await page.waitForSelector('[data-testid="filter-source"]');
  await page.select('[data-testid="filter-source"]', 'chesscom');

  await clickButtonByText(page, 'Run + Refresh');
  await page.waitForSelector('[data-testid="motif-breakdown"]');
  await page.waitForSelector('table');
  await new Promise((resolve) => setTimeout(resolve, 2000));

  await captureScreenshot(page, path.resolve(__dirname), screenshotName);

  await browser.close();

  if (consoleErrors.length) {
    console.error('Console errors detected:', consoleErrors);
    process.exit(1);
  }
})();
