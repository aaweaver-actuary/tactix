const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const {
  closeFiltersModal,
  openFiltersModal,
} = require('./helpers/filters_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_HEADER =
  process.env.TACTIX_SCREENSHOT_HEADER ||
  'feature-source-filter-header-2026-02-10.png';
const SCREENSHOT_MODAL =
  process.env.TACTIX_SCREENSHOT_MODAL ||
  'feature-source-filter-modal-2026-02-10.png';
const HERO_SELECTOR = '[data-testid="dashboard-hero"]';
const SOURCE_LABELS = ['All sites', 'Lichess · Rapid', 'Chess.com · Blitz'];

function resolveNextSource(current) {
  if (current === 'lichess') return 'chesscom';
  return 'lichess';
}

function resolveHeadingToken(source) {
  return source === 'chesscom' ? 'Chess.com' : 'Lichess';
}

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector(HERO_SELECTOR, { timeout: 60000 });

    const hasHeaderSelector = await page.evaluate(
      (selector, labels) => {
        const hero = document.querySelector(selector);
        if (!hero) return false;
        const buttonLabels = Array.from(hero.querySelectorAll('button')).map(
          (btn) => btn.textContent?.trim(),
        );
        return labels.some((label) => buttonLabels.includes(label));
      },
      HERO_SELECTOR,
      SOURCE_LABELS,
    );

    if (hasHeaderSelector) {
      throw new Error('Dashboard header still renders source selector buttons.');
    }

    const outDir = path.resolve(__dirname);
    const headerPath = await captureScreenshot(
      page,
      outDir,
      SCREENSHOT_HEADER,
    );
    console.log('Saved screenshot to', headerPath);

    await openFiltersModal(page);

    const currentSource = await page.$eval(
      '[data-testid="filter-source"]',
      (el) => el.value,
    );
    const nextSource = resolveNextSource(currentSource);
    await page.select('[data-testid="filter-source"]', nextSource);

    const headingToken = resolveHeadingToken(nextSource);
    await page.waitForFunction(
      (selector, token) => {
        const hero = document.querySelector(selector);
        const heading = hero?.querySelector('h1');
        return heading?.textContent?.toLowerCase().includes(token.toLowerCase());
      },
      { timeout: 60000 },
      HERO_SELECTOR,
      headingToken,
    );

    const modalPath = await captureScreenshot(page, outDir, SCREENSHOT_MODAL);
    console.log('Saved screenshot to', modalPath);

    await closeFiltersModal(page);

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
