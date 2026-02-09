const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_OPEN =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-settings-modal-open-2026-02-09.png';
const SCREENSHOT_CLOSED = 'feature-settings-modal-closed-2026-02-09.png';

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });

    await page.waitForSelector('[data-testid="filters-open"]', {
      timeout: 60000,
    });
    await page.click('[data-testid="filters-open"]');

    await page.waitForSelector('[data-testid="filters-modal"]', {
      visible: true,
      timeout: 60000,
    });
    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: 60000,
    });

    const outDir = path.resolve(__dirname);
    const openPath = await captureScreenshot(page, outDir, SCREENSHOT_OPEN);
    console.log('Saved screenshot to', openPath);

    await page.click('[data-testid="filters-modal-close"]');
    await page.waitForFunction(
      () => !document.querySelector('[data-testid="filters-modal"]'),
      { timeout: 60000 },
    );

    const closedPath = await captureScreenshot(page, outDir, SCREENSHOT_CLOSED);
    console.log('Saved screenshot to', closedPath);

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
