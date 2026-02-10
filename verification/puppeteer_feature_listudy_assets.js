const puppeteer = require('../client/node_modules/puppeteer');
const { selectSource } = require('./enter_submit_helpers');
const { waitForListudyAssets } = require('./listudy_assets_helpers');
const { ensureCardExpanded } = require('./helpers/client_e2e_helpers');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-listudy-assets-2026-02-08.png';
const source = process.env.TACTIX_SOURCE || 'chesscom';
const selectors = {
  positionsRow: '[data-testid^="positions-row-"]',
  chessboardModal: '[data-testid="chessboard-modal"]',
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to UI...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1');

    await selectSource(page, source);

    console.log('Opening a chessboard view to load listudy assets...');
    await ensureCardExpanded(page, 'dashboard-card-positions-list');
    await page.waitForSelector(selectors.positionsRow, { timeout: 60000 });
    await page.$eval(selectors.positionsRow, (row) => row.click());
    await page.waitForSelector(selectors.chessboardModal, { timeout: 60000 });

    await waitForListudyAssets(page, 60000);

    const outPath = await captureScreenshot(
      page,
      __dirname,
      screenshotName,
    );
    console.log('Saved screenshot to', outPath);

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }
  } catch (err) {
    try {
      const outPath = await captureScreenshot(
        page,
        __dirname,
        `failed-${screenshotName}`,
      );
      console.error('Saved failure screenshot to', outPath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Listudy asset verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
