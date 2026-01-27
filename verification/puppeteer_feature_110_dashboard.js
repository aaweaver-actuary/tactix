const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const baseUrl = process.env.TACTIX_DASHBOARD_URL || 'http://localhost:5173';
const source = process.env.TACTIX_SOURCE || 'lichess';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  `feature-110-dashboard-${source}-${new Date().toISOString().slice(0, 10)}.png`;

async function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
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
    const errorText = request.failure()?.errorText || 'unknown';
    if (errorText.includes('ERR_ABORTED')) return;
    consoleErrors.push(`Request failed: ${request.url()} (${errorText})`);
  });

  try {
    await page.goto(baseUrl, { waitUntil: 'networkidle0', timeout: 60000 });
    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: 60000,
    });

    if (source === 'chesscom') {
      await page.$$eval('button', (buttons) => {
        const target = buttons.find(
          (btn) => btn.textContent && btn.textContent.includes('Chess.com'),
        );
        if (target) target.click();
      });
    }

    await delay(2000);
    await page.waitForSelector('table', { timeout: 60000 });

    const outDir = path.resolve(__dirname);
    const outPath = path.join(outDir, screenshotName);
    fs.mkdirSync(outDir, { recursive: true });
    await page.screenshot({ path: outPath, fullPage: true });
    console.log('Saved screenshot to', outPath);

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      throw new Error('Console errors detected during UI verification');
    }
  } finally {
    await browser.close();
  }
})();
