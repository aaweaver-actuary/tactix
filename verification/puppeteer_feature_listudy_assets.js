const puppeteer = require('../client/node_modules/puppeteer');
const { selectSource } = require('./enter_submit_helpers');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-listudy-assets-2026-02-08.png';
const source = process.env.TACTIX_SOURCE || 'chesscom';

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to UI...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1');

    await selectSource(page, source);

    console.log('Refreshing metrics to load practice data...');
    await page.$$eval(
      'button',
      (buttons, label) => {
        const target = buttons.find(
          (btn) => btn.textContent && btn.textContent.includes(label),
        );
        if (target) target.click();
      },
      'Refresh metrics',
    );

    await page.waitForFunction(
      () =>
        Array.from(document.querySelectorAll('img')).some((img) =>
          img.getAttribute('src')?.includes('/pieces/cburnett/'),
        ),
      { timeout: 60000 },
    );

    await page.waitForFunction(
      () => {
        const card = document.querySelector('.card');
        if (!card) return false;
        const style = window.getComputedStyle(card);
        return style.backgroundImage.includes('listudy-brown');
      },
      { timeout: 60000 },
    );

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
