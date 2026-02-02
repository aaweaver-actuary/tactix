const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'issue-1-chesscom-bullet-pipeline-validation-2026-02-01.png';

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-testid="filter-source"]');

    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]');
    await page.select('[data-testid="filter-chesscom-profile"]', 'bullet');

    await page.select('[data-testid="filter-motif"]', 'hanging_piece');
    await page.click('[data-testid="filter-start-date"]', { clickCount: 3 });
    await page.type('[data-testid="filter-start-date"]', '2026-02-01');
    await page.keyboard.press('Tab');
    await page.click('[data-testid="filter-end-date"]', { clickCount: 3 });
    await page.type('[data-testid="filter-end-date"]', '2026-02-01');
    await page.keyboard.press('Tab');

    await new Promise((resolve) => setTimeout(resolve, 2000));
    await page.waitForSelector('[data-testid="recent-games-card"]');
    await page.waitForSelector('h3');

    const outPath = await captureScreenshot(
      page,
      path.resolve(__dirname),
      screenshotName,
    );

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
  } catch (err) {
    try {
      const outPath = await captureScreenshot(
        page,
        path.resolve(__dirname),
        `failed-${screenshotName}`,
      );
      console.error('Saved failure screenshot to', outPath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Issue 1 pipeline validation failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
