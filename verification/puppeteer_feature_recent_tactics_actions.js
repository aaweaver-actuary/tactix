const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const { selectSource } = require('./enter_submit_helpers');
const { ensureCardExpanded } = require('./helpers/client_e2e_helpers');
const {
  installLichessSpy,
  resetLichessSpy,
  waitForLichessUrl,
  assertLichessAnalysisUrl,
} = require('./helpers/lichess_open_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-recent-tactics-actions-2026-02-10.png';
const source = process.env.TACTIX_SOURCE || 'chesscom';

const selectors = {
  tacticsCard: 'dashboard-card-tactics-table',
  goToGame: '[data-testid^="tactics-go-to-game-"]',
  openLichess: '[data-testid^="tactics-open-lichess-"]',
  gameDetailModal: '[data-testid="game-detail-modal"]',
  gameDetailClose: '[data-testid="game-detail-close"]',
};

const findEnabledButton = async (page, selector) => {
  const buttons = await page.$$(selector);
  for (const button of buttons) {
    const isDisabled = await page.evaluate((node) => node.disabled, button);
    if (!isDisabled) return button;
  }
  throw new Error(`No enabled button found for selector: ${selector}`);
};

const ensureUnknownButtonsDisabled = async (page) => {
  const unknownButtons = await page.$$('[data-testid$="unknown"]');
  if (!unknownButtons.length) {
    console.log('No unknown tactic buttons found; skipping disabled check.');
    return;
  }
  const states = await Promise.all(
    unknownButtons.map((button) =>
      page.evaluate((node) => node.disabled, button),
    ),
  );
  if (!states.every(Boolean)) {
    throw new Error('Expected unknown tactic buttons to be disabled.');
  }
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await selectSource(page, source);
    await ensureCardExpanded(page, selectors.tacticsCard);

    await page.waitForSelector(selectors.goToGame, { timeout: 60000 });
    await page.waitForSelector(selectors.openLichess, { timeout: 60000 });

    await ensureUnknownButtonsDisabled(page);

    await installLichessSpy(page);
    const openLichessButton = await findEnabledButton(page, selectors.openLichess);
    await resetLichessSpy(page);
    await openLichessButton.click();
    const url = await waitForLichessUrl(page, 15000);
    assertLichessAnalysisUrl(url);

    const goToGameButton = await findEnabledButton(page, selectors.goToGame);
    await goToGameButton.click();
    await page.waitForSelector(selectors.gameDetailModal, { timeout: 60000 });

    const outPath = await captureScreenshot(
      page,
      path.resolve(__dirname),
      screenshotName,
    );
    console.log('Saved screenshot to', outPath);

    await page.click(selectors.gameDetailClose);

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
