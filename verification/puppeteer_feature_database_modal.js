const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-fab-database-modal-2026-02-10.png';

const selectors = {
  fabToggle: '[data-testid="fab-toggle"]',
  databaseOpen: '[data-testid="database-open"]',
  modal: '[data-testid="database-modal"]',
  postgresStatus: '[data-testid="postgres-status"]',
  postgresRaw: '[data-testid="postgres-raw-pgns"]',
  postgresAnalysis: '[data-testid="postgres-analysis"]',
};

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });

    const dashboardHasPostgres = await page.evaluate((sel) => {
      return Boolean(
        document.querySelector(sel.postgresStatus) ||
          document.querySelector(sel.postgresRaw) ||
          document.querySelector(sel.postgresAnalysis),
      );
    }, selectors);

    if (dashboardHasPostgres) {
      throw new Error('Postgres cards should not render on the dashboard.');
    }

    await page.waitForSelector(selectors.fabToggle, { timeout: 60000 });
    await page.click(selectors.fabToggle);
    await page.waitForSelector(selectors.databaseOpen, { timeout: 60000 });
    await page.click(selectors.databaseOpen);

    await page.waitForSelector(selectors.modal, { timeout: 60000 });

    const modalHasContent = await page.evaluate((sel) => {
      const modal = document.querySelector(sel.modal);
      if (!modal) return false;
      const hasPostgresCards = Boolean(
        modal.querySelector(sel.postgresStatus) ||
          modal.querySelector(sel.postgresRaw) ||
          modal.querySelector(sel.postgresAnalysis),
      );
      const hasPostgresText = (modal.textContent || '').includes('Postgres');
      return hasPostgresCards || hasPostgresText;
    }, selectors);

    if (!modalHasContent) {
      throw new Error('Database modal did not render expected Postgres content.');
    }

    const outPath = await captureScreenshot(page, path.resolve(__dirname), screenshotName);
    console.log('Saved screenshot to', outPath);

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
