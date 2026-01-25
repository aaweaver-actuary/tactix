const puppeteer = require('../client/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME || 'feature-028-practice-next-unseen.png';
const source = process.env.TACTIX_SOURCE || 'lichess';

async function selectSource(page) {
  if (source !== 'chesscom') return;
  const selector = 'select[data-testid="filter-source"]';
  const selectHandle = await page.$(selector);
  if (selectHandle) {
    await page.select(selector, 'chesscom');
    return;
  }
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

  try {
    console.log('Navigating to UI...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });

    await selectSource(page);

    await page.waitForSelector('body', { timeout: 60000 });
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });
    console.log('Saved screenshot to', outPath);

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
  } catch (err) {
    try {
      const outDir = path.resolve(__dirname);
      fs.mkdirSync(outDir, { recursive: true });
      const outPath = path.join(outDir, `failed-${screenshotName}`);
      await page.screenshot({ path: outPath, fullPage: true });
      console.error('Saved failure screenshot to', outPath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Feature 028 verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
