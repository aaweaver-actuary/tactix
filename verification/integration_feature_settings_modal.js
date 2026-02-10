const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const {
  closeFiltersModal,
  openFiltersModal,
} = require('./helpers/filters_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });

    const hasFiltersCard = await page.evaluate(() =>
      Boolean(document.querySelector('[data-testid="dashboard-card-filters"]')),
    );

    if (hasFiltersCard) {
      throw new Error('Filters card should not render on the dashboard.');
    }

    const fabReady = await page.evaluate(() => {
      const toggle = document.querySelector('[data-testid="fab-toggle"]');
      const action = document.querySelector('[data-testid="filters-open"]');
      return Boolean(
        toggle && toggle.getAttribute('aria-expanded') === 'false' && !action,
      );
    });

    if (!fabReady) {
      throw new Error('Floating action button did not render as expected.');
    }

    await openFiltersModal(page);

    const hasFilterInputs = await page.evaluate(() => {
      const modal = document.querySelector('[data-testid="filters-modal"]');
      const source = modal?.querySelector('[data-testid="filter-source"]');
      const motif = modal?.querySelector('[data-testid="filter-motif"]');
      return Boolean(source && motif);
    });

    if (!hasFilterInputs) {
      throw new Error('Filters modal did not render expected inputs.');
    }

    await closeFiltersModal(page);

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
