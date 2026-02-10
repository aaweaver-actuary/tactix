const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const {
  closeFiltersModal,
  openFiltersModal,
} = require('./helpers/filters_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
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
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
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
      throw new Error('Header still shows the source selector buttons.');
    }

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

    await closeFiltersModal(page);

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Source filter integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
