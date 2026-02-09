const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const {
  openFiltersModal,
  closeFiltersModalWithEscape,
} = require('./helpers/filters_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_OPEN =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-modal-escape-open-2026-02-09.png';
const SCREENSHOT_CLOSED = 'feature-modal-escape-closed-2026-02-09.png';

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });

    await openFiltersModal(page);

    const outDir = path.resolve(__dirname);
    const openPath = await captureScreenshot(page, outDir, SCREENSHOT_OPEN);
    console.log('Saved screenshot to', openPath);

    await closeFiltersModalWithEscape(page);

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
