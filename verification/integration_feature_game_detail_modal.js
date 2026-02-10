const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const {
  waitForDashboard,
  openRecentGamesTable,
  ensureRecentGamesHasRows,
} = require('./helpers/game_detail_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'lichess';

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await waitForDashboard(page, targetUrl, source);
    await openRecentGamesTable(page);
    await ensureRecentGamesHasRows(page);

    await page.waitForSelector('[data-testid^="go-to-game-"]');
    const buttons = await page.$$('[data-testid^="go-to-game-"]');
    if (!buttons.length) {
      throw new Error('Go to Game button not found in recent games modal');
    }
    await buttons[0].click();
    await page.waitForSelector('[data-testid="game-detail-modal"]', {
      visible: true,
    });
    await page.waitForSelector('[data-testid="game-detail-moves"]');
    await page.waitForSelector('[data-testid="game-detail-close"]');

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Game detail modal overlay integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
