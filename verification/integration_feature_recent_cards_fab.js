const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';

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

const waitForModalToClose = async (page, selector) => {
  await page.waitForFunction(
    (modalSelector) => !document.querySelector(modalSelector),
    { timeout: 60000 },
    selector,
  );
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });

    const dashboardHasCards = await page.evaluate((sel) => {
      return Boolean(
        document.querySelector(sel.recentGamesCard) ||
          document.querySelector(sel.recentTacticsCard),
      );
    }, selectors);

    if (dashboardHasCards) {
      throw new Error('Recent games/tactics cards should not render on the dashboard.');
    }

    await page.waitForSelector(selectors.fabToggle, { timeout: 60000 });
    await page.click(selectors.fabToggle);
    await page.waitForSelector(selectors.recentGamesOpen, { timeout: 60000 });
    await page.click(selectors.recentGamesOpen);
    await page.waitForSelector(selectors.recentGamesModal, { timeout: 60000 });
    await page.waitForSelector(selectors.recentGamesRow, { timeout: 60000 });

    await page.click(selectors.recentGamesClose);
    await waitForModalToClose(page, selectors.recentGamesModal);

    await page.click(selectors.fabToggle);
    await page.waitForSelector(selectors.recentTacticsOpen, { timeout: 60000 });
    await page.click(selectors.recentTacticsOpen);
    await page.waitForSelector(selectors.recentTacticsModal, { timeout: 60000 });
    await page.waitForSelector(selectors.recentTacticsRow, { timeout: 60000 });

    await page.click(selectors.recentTacticsClose);
    await waitForModalToClose(page, selectors.recentTacticsModal);

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Recent games/tactics FAB modals integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
