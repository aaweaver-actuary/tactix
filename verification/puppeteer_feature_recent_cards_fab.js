const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_GAMES =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-fab-recent-games-2026-02-10.png';
const SCREENSHOT_TACTICS = 'feature-fab-recent-tactics-2026-02-10.png';

const selectors = {
  fabToggle: '[data-testid="fab-toggle"]',
  recentGamesOpen: '[data-testid="recent-games-open"]',
  recentTacticsOpen: '[data-testid="recent-tactics-open"]',
  recentGamesModal: '[data-testid="recent-games-modal"]',
  recentTacticsModal: '[data-testid="recent-tactics-modal"]',
  recentGamesRow: '[data-testid^="recent-games-row-"]',
  recentTacticsRow: '[data-testid^="dashboard-game-row-"]',
  recentGamesClose: '[data-testid="recent-games-modal-close"]',
  recentTacticsClose: '[data-testid="recent-tactics-modal-close"]',
  recentGamesCard: '[data-testid="dashboard-card-recent-games"]',
  recentTacticsCard: '[data-testid="dashboard-card-tactics-table"]',
};

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });

    const hasRecentGamesCard = await page.$(selectors.recentGamesCard);
    const hasRecentTacticsCard = await page.$(selectors.recentTacticsCard);
    if (hasRecentGamesCard || hasRecentTacticsCard) {
      throw new Error('Recent games/tactics cards should not render on the dashboard.');
    }

    await page.waitForSelector(selectors.fabToggle, { timeout: 60000 });
    await page.click(selectors.fabToggle);
    await page.waitForSelector(selectors.recentGamesOpen, { timeout: 60000 });
    await page.click(selectors.recentGamesOpen);
    await page.waitForSelector(selectors.recentGamesModal, { timeout: 60000 });
    await page.waitForSelector(selectors.recentGamesRow, { timeout: 60000 });

    const outDir = path.resolve(__dirname);
    const gamesPath = await captureScreenshot(
      page,
      outDir,
      SCREENSHOT_GAMES,
    );
    console.log('Saved screenshot to', gamesPath);

    await page.click(selectors.recentGamesClose);
    await page.waitForFunction(
      (modalSelector) => !document.querySelector(modalSelector),
      { timeout: 60000 },
      selectors.recentGamesModal,
    );

    await page.click(selectors.fabToggle);
    await page.waitForSelector(selectors.recentTacticsOpen, { timeout: 60000 });
    await page.click(selectors.recentTacticsOpen);
    await page.waitForSelector(selectors.recentTacticsModal, { timeout: 60000 });
    await page.waitForSelector(selectors.recentTacticsRow, { timeout: 60000 });

    const tacticsPath = await captureScreenshot(
      page,
      outDir,
      SCREENSHOT_TACTICS,
    );
    console.log('Saved screenshot to', tacticsPath);

    await page.click(selectors.recentTacticsClose);

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
