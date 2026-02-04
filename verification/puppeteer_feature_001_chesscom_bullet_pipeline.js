const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const UI_BASE = process.env.TACTIX_UI_BASE || 'http://localhost:5173';
const SELECT_TIMEOUT_MS = 60000;
const BACKFILL_TIMEOUT_MS = 240000;

const attachConsoleCapture = (page) => {
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

  return consoleErrors;
};

const captureScreenshot = async (page, screenshotName) => {
  const outDir = path.resolve(__dirname);
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, screenshotName);
  await page.screenshot({ path: outPath, fullPage: true });
  return outPath;
};

const setDateInput = async (page, testId, value) => {
  await page.waitForSelector(`[data-testid="${testId}"]`, {
    timeout: SELECT_TIMEOUT_MS,
  });
  await page.$eval(
    `[data-testid="${testId}"]`,
    (input, dateValue) => {
      input.value = dateValue;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    },
    value,
  );
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(UI_BASE, {
      waitUntil: 'networkidle0',
      timeout: SELECT_TIMEOUT_MS,
    });
    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: SELECT_TIMEOUT_MS,
    });

    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]', {
      timeout: SELECT_TIMEOUT_MS,
    });
    await page.select('[data-testid="filter-chesscom-profile"]', 'bullet');

    await setDateInput(page, 'backfill-start', '2026-02-01');
    await setDateInput(page, 'backfill-end', '2026-02-01');

    await page.waitForSelector('[data-testid="action-backfill"]', {
      timeout: SELECT_TIMEOUT_MS,
    });
    await page.click('[data-testid="action-backfill"]');

    await page.waitForFunction(
      () => document.querySelector('[data-testid="action-backfill"]')?.disabled,
      { timeout: BACKFILL_TIMEOUT_MS },
    );
    await page.waitForFunction(
      () =>
        !document.querySelector('[data-testid="action-backfill"]')?.disabled,
      { timeout: BACKFILL_TIMEOUT_MS },
    );

    await page.waitForSelector('[data-testid="motif-breakdown"]', {
      timeout: SELECT_TIMEOUT_MS,
    });
    await page.waitForSelector('[data-testid="practice-queue-card"]', {
      timeout: SELECT_TIMEOUT_MS,
    });

    const outPath = await captureScreenshot(
      page,
      'feature-001-chesscom-bullet-pipeline-2026-02-04.png',
    );
    console.log('Saved screenshot to', outPath);

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
  } catch (err) {
    try {
      const outPath = await captureScreenshot(
        page,
        'failed-feature-001-chesscom-bullet-pipeline-2026-02-04.png',
      );
      console.error('Saved failure screenshot to', outPath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('UI verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
