const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const {
  waitForDashboard,
  openRecentGamesTable,
  ensureRecentGamesHasRows,
  waitForRecentGamesRowReady,
} = require('./helpers/game_detail_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'lichess';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-recent-games-go-to-game-2026-02-10.png';

const SELECTORS = {
  row: '[data-testid^="recent-games-row-"]',
  goToGameButton: '[data-testid^="go-to-game-"]',
  openLichessButton: '[data-testid^="open-lichess-"]',
  gameDetailModal: '[data-testid="game-detail-modal"]',
  gameDetailMoves: '[data-testid="game-detail-moves"]',
};

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await waitForDashboard(page, targetUrl, source);
    await openRecentGamesTable(page);
    await ensureRecentGamesHasRows(page);
    await waitForRecentGamesRowReady(page);

    await page.waitForSelector(SELECTORS.row);
    await page.waitForSelector(SELECTORS.goToGameButton);

    const layoutOk = await page.evaluate((selectors) => {
      const row = document.querySelector(selectors.row);
      if (!row) return false;
      const goToGame = row.querySelector(selectors.goToGameButton);
      const openLichess = row.querySelector(selectors.openLichessButton);
      if (!goToGame || !openLichess) return false;
      const label = goToGame.getAttribute('aria-label') || '';
      return Boolean(label);
    }, SELECTORS);

    if (!layoutOk) {
      throw new Error('Go to Game button layout/accessibility check failed.');
    }

    const goToGame = await page.$(
      `${SELECTORS.goToGameButton}:not([disabled])`,
    );
    if (!goToGame) {
      throw new Error('No enabled Go to Game button found.');
    }

    await goToGame.click();
    await page.waitForSelector(SELECTORS.gameDetailModal, { visible: true });
    await page.waitForSelector(SELECTORS.gameDetailMoves);

    const outPath = await captureScreenshot(
      page,
      path.resolve(__dirname),
      SCREENSHOT_NAME,
    );
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
