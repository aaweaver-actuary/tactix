const puppeteer = require('../client/node_modules/puppeteer');
const { selectSource } = require('./enter_submit_helpers');
const { ensureCardExpanded } = require('./helpers/client_e2e_helpers');
const {
  installLichessSpy,
  resetLichessSpy,
  waitForLichessUrl,
  assertLichessAnalysisUrl,
  getLichessSpyState,
} = require('./helpers/lichess_open_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'chesscom';

const selectors = {
  tacticsCard: 'dashboard-card-tactics-table',
  goToGame: '[data-testid^="tactics-go-to-game-"]',
  openLichess: '[data-testid^="tactics-open-lichess-"]',
  gameDetailModal: '[data-testid="game-detail-modal"]',
};

const findEnabledButton = async (page, selector) => {
  const buttons = await page.$$(selector);
  for (const button of buttons) {
    const isDisabled = await page.evaluate((node) => node.disabled, button);
    if (!isDisabled) return button;
  }
  throw new Error(`No enabled button found for selector: ${selector}`);
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(err.toString()));
  page.on('requestfailed', (request) => {
    consoleErrors.push(
      `Request failed: ${request.url()} (${request.failure()?.errorText || 'unknown'})`,
    );
  });

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await selectSource(page, source);
    await ensureCardExpanded(page, selectors.tacticsCard);

    await page.waitForSelector(selectors.goToGame, { timeout: 60000 });
    await page.waitForSelector(selectors.openLichess, { timeout: 60000 });

    const unknownButtons = await page.$$('[data-testid$="unknown"]');
    if (unknownButtons.length) {
      const states = await Promise.all(
        unknownButtons.map((button) =>
          page.evaluate((node) => node.disabled, button),
        ),
      );
      if (!states.every(Boolean)) {
        throw new Error('Expected unknown tactic buttons to be disabled.');
      }
    }

    await installLichessSpy(page);
    const openLichessButton = await findEnabledButton(page, selectors.openLichess);
    await resetLichessSpy(page);
    await openLichessButton.click();
    let url = '';
    try {
      url = await waitForLichessUrl(page, 30000);
    } catch (err) {
      const state = await getLichessSpyState(page);
      throw new Error(
        `Lichess URL capture timed out. openCount=${state.openCount} lastOpenArgs=${state.lastOpenArgs}`,
      );
    }
    assertLichessAnalysisUrl(url);

    const goToGameButton = await findEnabledButton(page, selectors.goToGame);
    await goToGameButton.click();
    await page.waitForSelector(selectors.gameDetailModal, { timeout: 60000 });

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Recent tactics actions verified.');
  } finally {
    await browser.close();
  }
})();
