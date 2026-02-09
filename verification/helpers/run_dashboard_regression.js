const fs = require('fs');
const path = require('path');
const puppeteer = require('../../client/node_modules/puppeteer');

const SELECT_TIMEOUT_MS = 60000;
const MOTIF_TIMEOUT_MS = 120000;
const POST_RUN_DELAY_MS = 2000;

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
  const outDir = path.resolve(__dirname, '..');
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, screenshotName);
  await page.screenshot({ path: outPath, fullPage: true });
  return outPath;
};

const openFiltersModal = async (page) => {
  const modalSelector = '[data-testid="filters-modal"]';
  if (await page.$(modalSelector)) return;
  await page.waitForSelector('[data-testid="filters-open"]', {
    timeout: SELECT_TIMEOUT_MS,
  });
  await page.click('[data-testid="filters-open"]');
  await page.waitForSelector(modalSelector, { timeout: SELECT_TIMEOUT_MS });
};

const closeFiltersModal = async (page) => {
  const modalSelector = '[data-testid="filters-modal"]';
  if (!(await page.$(modalSelector))) return;
  const closeButton = await page.$('[data-testid="filters-modal-close"]');
  if (closeButton) {
    await closeButton.click();
  } else {
    await page.click(modalSelector);
  }
  await page.waitForFunction(
    (selector) => !document.querySelector(selector),
    { timeout: SELECT_TIMEOUT_MS },
    modalSelector,
  );
};

const runDashboardRegression = async ({
  targetUrl,
  screenshotName,
  sourceValue,
  profileTestId,
  profileValue,
  waitUntil = 'networkidle0',
  actionTestId = 'action-run',
  motifTestId = 'motif-breakdown',
  tableSelector = 'table',
  waitForTable = true,
  failureMessage = 'Regression verification failed',
}) => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil, timeout: SELECT_TIMEOUT_MS });
    await openFiltersModal(page);
    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: SELECT_TIMEOUT_MS,
    });

    if (sourceValue) {
      await page.select('[data-testid="filter-source"]', sourceValue);
    }

    if (profileTestId && profileValue) {
      await page.waitForSelector(`[data-testid="${profileTestId}"]`, {
        timeout: SELECT_TIMEOUT_MS,
      });
      await page.select(`[data-testid="${profileTestId}"]`, profileValue);
    }

    await closeFiltersModal(page);

    await page.waitForSelector(`[data-testid="${actionTestId}"]`, {
      timeout: SELECT_TIMEOUT_MS,
    });
    await page.click(`[data-testid="${actionTestId}"]`);

    await page.waitForSelector(`[data-testid="${motifTestId}"]`, {
      timeout: MOTIF_TIMEOUT_MS,
    });
    if (waitForTable) {
      await page.waitForSelector(tableSelector);
    }
    await new Promise((resolve) => setTimeout(resolve, POST_RUN_DELAY_MS));

    await captureScreenshot(page, screenshotName);

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
  } catch (err) {
    try {
      const outPath = await captureScreenshot(page, `failed-${screenshotName}`);
      console.error('Saved failure screenshot to', outPath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error(`${failureMessage}:`, err);
    process.exit(1);
  } finally {
    await browser.close();
  }
};

module.exports = { runDashboardRegression };
