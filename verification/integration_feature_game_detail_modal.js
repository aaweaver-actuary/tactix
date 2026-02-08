const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture } = require('./helpers/puppeteer_capture');
const { selectSource } = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'lichess';

async function getTextContent(handle) {
  if (!handle) return '';
  const prop = await handle.getProperty('textContent');
  const value = await prop.jsonValue();
  return value ? String(value) : '';
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('[data-testid="filter-source"]');
    await selectSource(page, source);
    await page.waitForSelector('[data-testid="action-run"]');
    await page.click('[data-testid="action-run"]');
    await new Promise((resolve) => setTimeout(resolve, 2000));
    await page.waitForSelector('[data-testid="dashboard-card-tactics-table"]');

    await page.click('[data-testid="recent-games-card"] [role="button"]');
    await page.waitForSelector('[data-testid="recent-games-card"] table');

    const firstRow = await page.waitForSelector(
      '[data-testid="recent-games-card"] table tbody tr',
    );
    const firstRowText = await getTextContent(firstRow);
    if (firstRowText.toLowerCase().includes('no rows')) {
      throw new Error('No recent games rows found for selected source');
    }

    await page.click('[data-testid="recent-games-card"] table tbody tr');
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
