const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const {
  openFiltersModal,
  closeFiltersModalWithEscape,
} = require('./helpers/filters_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await openFiltersModal(page);

    await closeFiltersModalWithEscape(page);

    const modalExists = await page.evaluate(
      () => Boolean(document.querySelector('[data-testid="filters-modal"]')),
    );

    if (modalExists) {
      throw new Error('Expected filters modal to close on Escape.');
    }

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Modal Escape key integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
