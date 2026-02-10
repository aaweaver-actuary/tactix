const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const HERO_SELECTOR = '[data-testid="dashboard-hero"]';
const REQUIRED_TEST_IDS = [
  'action-run',
  'action-backfill',
  'action-migrate',
  'action-refresh',
  'backfill-start',
  'backfill-end',
];

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector(HERO_SELECTOR, { timeout: 60000 });

    const heroStatus = await page.evaluate((selector, required) => {
      const hero = document.querySelector(selector);
      if (!hero) return { ok: false, missing: required };
      const missing = required.filter(
        (id) => !hero.querySelector(`[data-testid="${id}"]`),
      );
      const hasHeroClass = hero.classList.contains('hero-card');
      return { ok: missing.length === 0 && hasHeroClass, missing, hasHeroClass };
    }, HERO_SELECTOR, REQUIRED_TEST_IDS);

    if (!heroStatus.ok) {
      const missing = heroStatus.missing.length
        ? `Missing test ids: ${heroStatus.missing.join(', ')}.`
        : '';
      const classNote = heroStatus.hasHeroClass ? '' : 'Hero class missing.';
      throw new Error(`${missing} ${classNote}`.trim());
    }

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Hero redesign integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
