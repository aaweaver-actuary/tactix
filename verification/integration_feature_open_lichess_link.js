const puppeteer = require('../client/node_modules/puppeteer');
const { selectSource } = require('./enter_submit_helpers');
const {
  installLichessSpy,
  resetLichessSpy,
  waitForLichessUrl,
  assertLichessAnalysisUrl,
} = require('./helpers/lichess_open_helpers');
const {
  openRecentGamesTable,
  ensureRecentGamesHasRows,
  waitForRecentGamesRowReady,
} = require('./helpers/game_detail_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'chesscom';

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
    await page.waitForSelector('[data-testid="filter-source"]');
    await installLichessSpy(page);
    await selectSource(page, source);
    await page.waitForSelector('[data-testid="action-run"]');
    await page.click('[data-testid="action-run"]');

    await openRecentGamesTable(page);
    await ensureRecentGamesHasRows(page);
    await waitForRecentGamesRowReady(page);
    await page.waitForSelector('[data-testid^="open-lichess-"]');

    const buttons = await page.$$('[data-testid^="open-lichess-"]');
    if (!buttons.length) {
      throw new Error('Open in Lichess button missing.');
    }

    await resetLichessSpy(page);
    await buttons[0].click();
    const url = await waitForLichessUrl(page, 15000);
    assertLichessAnalysisUrl(url);

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Open in Lichess link verified.');
  } finally {
    await browser.close();
  }
})();
