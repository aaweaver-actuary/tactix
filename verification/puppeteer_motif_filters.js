const puppeteer = require('../client/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');
const { openFiltersModal, closeFiltersModal } = require('./helpers/filters_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME || 'dashboard-motif-filters.png';

const dashboardResponse = (url, response) =>
  url.includes('/api/dashboard') && response.status() === 200;

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
  await openFiltersModal(page);
  await page.waitForSelector('[data-testid="filter-motif"]');
  await page.waitForSelector('[data-testid="motif-breakdown"]');

  const motifValues = await page.$$eval(
    'select[data-testid="filter-motif"] option',
    (options) => options.map((opt) => opt.value),
  );
  const motifChoice = motifValues.find((value) => value && value !== 'all');

  if (motifChoice) {
    await Promise.all([
      page.waitForResponse((response) =>
        dashboardResponse(response.url(), response),
      ),
      page.select('select[data-testid="filter-motif"]', motifChoice),
    ]);
  }

  const timeControlValues = await page.$$eval(
    'select[data-testid="filter-time-control"] option',
    (options) => options.map((opt) => opt.value),
  );
  const timeChoice = timeControlValues.find(
    (value) => value && value !== 'all',
  );

  if (timeChoice) {
    await Promise.all([
      page.waitForResponse((response) =>
        dashboardResponse(response.url(), response),
      ),
      page.select('select[data-testid="filter-time-control"]', timeChoice),
    ]);
  }

  const ratingValues = await page.$$eval(
    'select[data-testid="filter-rating"] option',
    (options) => options.map((opt) => opt.value),
  );
  const ratingChoice = ratingValues.find(
    (value) => value && value !== 'all',
  );

  if (ratingChoice) {
    await Promise.all([
      page.waitForResponse((response) =>
        dashboardResponse(response.url(), response),
      ),
      page.select('select[data-testid="filter-rating"]', ratingChoice),
    ]);
  }

  await new Promise((resolve) => setTimeout(resolve, 1500));
  await closeFiltersModal(page);

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
