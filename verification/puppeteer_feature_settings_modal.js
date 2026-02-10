const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const {
  closeFiltersModal,
  openFiltersModal,
} = require('./helpers/filters_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_OPEN_DESKTOP =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-fab-filters-open-desktop-2026-02-09.png';
const SCREENSHOT_CLOSED_DESKTOP =
  'feature-fab-filters-closed-desktop-2026-02-09.png';
const SCREENSHOT_OPEN_MOBILE =
  'feature-fab-filters-open-mobile-2026-02-09.png';
const SCREENSHOT_CLOSED_MOBILE =
  'feature-fab-filters-closed-mobile-2026-02-09.png';

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });

    const outDir = path.resolve(__dirname);

    await openFiltersModal(page);
    const openPath = await captureScreenshot(
      page,
      outDir,
      SCREENSHOT_OPEN_DESKTOP,
    );
    console.log('Saved screenshot to', openPath);

    await closeFiltersModal(page);
    const closedPath = await captureScreenshot(
      page,
      outDir,
      SCREENSHOT_CLOSED_DESKTOP,
    );
    console.log('Saved screenshot to', closedPath);

    await page.setViewport({
      width: 390,
      height: 844,
      deviceScaleFactor: 2,
      isMobile: true,
      hasTouch: true,
    });
    await new Promise((resolve) => setTimeout(resolve, 400));

    await openFiltersModal(page);
    const openMobilePath = await captureScreenshot(
      page,
      outDir,
      SCREENSHOT_OPEN_MOBILE,
    );
    console.log('Saved screenshot to', openMobilePath);

    await closeFiltersModal(page);
    const closedMobilePath = await captureScreenshot(
      page,
      outDir,
      SCREENSHOT_CLOSED_MOBILE,
    );
    console.log('Saved screenshot to', closedMobilePath);

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
