const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-049-chesscom-classical-incremental-2026-01-25.png';

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
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: 60000,
    });

    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]', {
      timeout: 60000,
    });
    await page.select('[data-testid="filter-chesscom-profile"]', 'classical');

    await page.waitForSelector('[data-testid="action-run"]', {
      timeout: 60000,
    });
    await page.click('[data-testid="action-run"]');

    await page.waitForSelector('[data-testid="motif-breakdown"]', {
      timeout: 120000,
    });
    await page.waitForSelector('table');
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });

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
    console.error('Feature 049 verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
