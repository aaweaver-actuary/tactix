const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('[data-testid="filters-open"]', {
      timeout: 60000,
    });

    await page.click('[data-testid="filters-open"]');
    await page.waitForSelector('[data-testid="filters-modal"]', {
      timeout: 60000,
    });

    const hasFilterInputs = await page.evaluate(() => {
      const modal = document.querySelector('[data-testid="filters-modal"]');
      const source = modal?.querySelector('[data-testid="filter-source"]');
      const motif = modal?.querySelector('[data-testid="filter-motif"]');
      return Boolean(source && motif);
    });

    if (!hasFilterInputs) {
      throw new Error('Filters modal did not render expected inputs.');
    }

    await page.click('[data-testid="filters-modal-close"]');
    await page.waitForFunction(
      () => !document.querySelector('[data-testid="filters-modal"]'),
      { timeout: 60000 },
    );

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Settings modal integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
