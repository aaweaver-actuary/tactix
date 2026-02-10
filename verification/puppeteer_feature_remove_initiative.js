const puppeteer = require('../client/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');
const { openFiltersModal, closeFiltersModal } = require('./helpers/filters_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-remove-initiative-2026-02-09.png';

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
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
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await openFiltersModal(page);
    await page.waitForSelector('[data-testid="filter-motif"]');
    await page.waitForSelector('[data-testid="motif-breakdown"]');

    const motifValues = await page.$$eval(
      'select[data-testid="filter-motif"] option',
      (options) =>
        options.map((opt) => ({
          value: opt.value,
          label: opt.textContent || '',
        })),
    );

    const hasInitiativeOption = motifValues.some(
      (opt) =>
        opt.value.toLowerCase() === 'initiative' ||
        opt.label.toLowerCase().includes('initiative'),
    );
    assert(!hasInitiativeOption, 'Initiative motif still appears in filter options');

    const motifBreakdownText = await page.$eval(
      '[data-testid="motif-breakdown"]',
      (element) => (element.textContent || '').toLowerCase(),
    );
    assert(
      !motifBreakdownText.includes('initiative'),
      'Initiative motif still appears in the motif breakdown card',
    );

    await closeFiltersModal(page);

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
  } catch (err) {
    console.error('Initiative removal UI check failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
