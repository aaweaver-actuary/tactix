const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const {
  getHeroStatus,
  waitForHero,
} = require('./helpers/hero_redesign_helpers');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await waitForHero(page);
    const heroStatus = await getHeroStatus(page);

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
