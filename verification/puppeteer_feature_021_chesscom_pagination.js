const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

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
  const consoleErrors = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(err.toString()));
  page.on('requestfailed', (request) => {
    consoleErrors.push(
      `Request failed: ${request.url()} (${request.failure()?.errorText || 'unknown'})`,
    );
  });

  await page.goto(targetUrl, { waitUntil: 'networkidle0' });
  await page.waitForSelector('[data-testid="filter-source"]');
  await page.select('[data-testid="filter-source"]', 'chesscom');

  await clickButtonByText(page, 'Run + Refresh');
  await page.waitForSelector('[data-testid="motif-breakdown"]');
  await page.waitForSelector('table');
  await new Promise((resolve) => setTimeout(resolve, 2000));

  const outDir = path.resolve(__dirname);
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, screenshotName);
  await page.screenshot({ path: outPath, fullPage: true });

  await browser.close();

  if (consoleErrors.length) {
    console.error('Console errors detected:', consoleErrors);
    process.exit(1);
  }
})();
