const puppeteer = require('../client/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-030-practice-session-progress.png';

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

    await page.waitForSelector('[data-testid="practice-session-progress"]', {
      timeout: 60000,
    });
    await page.waitForSelector('[data-testid="practice-progress-fill"]', {
      timeout: 60000,
    });
    await page.waitForSelector('[data-testid="practice-streak-progress"]', {
      timeout: 60000,
    });

    const progressSnapshot = await page.evaluate(() => {
      const summary = document.querySelector(
        '[data-testid="practice-session-summary"]',
      );
      const progress = document.querySelector(
        '[data-testid="practice-progress-bar"]',
      );
      const streak = document.querySelector(
        '[data-testid="practice-streak-progress"]',
      );
      return {
        summaryText: summary?.textContent || '',
        progressNow: progress?.getAttribute('aria-valuenow'),
        streakNow: streak?.getAttribute('aria-valuenow'),
      };
    });

    if (!progressSnapshot.summaryText) {
      throw new Error('Practice session summary text missing.');
    }
    if (progressSnapshot.progressNow === null) {
      throw new Error('Practice progress bar aria-valuenow missing.');
    }
    if (progressSnapshot.streakNow === null) {
      throw new Error('Practice streak bar aria-valuenow missing.');
    }

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
    console.error('Practice session verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
