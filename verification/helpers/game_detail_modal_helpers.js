const { selectSource } = require('../enter_submit_helpers');

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function getTextContent(handle) {
  if (!handle) return '';
  const prop = await handle.getProperty('textContent');
  const value = await prop.jsonValue();
  return value ? String(value) : '';
}

async function waitForDashboard(page, targetUrl, source) {
  await page.goto(targetUrl, { waitUntil: 'networkidle0' });
  await selectSource(page, source);
  await page.waitForSelector('[data-testid="dashboard-card-tactics-table"]');
}

async function waitForCardExpanded(page, cardSelector) {
  await page.waitForFunction(
    (selector) => {
      const node = document.querySelector(selector);
      return node && node.getAttribute('data-state') === 'expanded';
    },
    { timeout: 60000 },
    `${cardSelector} [data-state]`,
  );
  await page.waitForSelector(`${cardSelector} table`);
}

async function getRecentGamesRowText(page) {
  const row = await page.waitForSelector(
    '[data-testid="recent-games-card"] table tbody tr',
  );
  return getTextContent(row);
}

async function openRecentGamesTable(page) {
  const cardSelector = '[data-testid="recent-games-card"]';
  const headerSelector = `${cardSelector} [role="button"]`;
  await page.waitForSelector(headerSelector);
  const isCollapsed = await page.$eval(
    headerSelector,
    (header) => header.getAttribute('aria-expanded') === 'false',
  );
  if (isCollapsed) {
    await page.click(headerSelector);
  }
  await waitForCardExpanded(page, cardSelector);
}

async function ensureRecentGamesHasRows(page) {
  const firstRowText = await getRecentGamesRowText(page);
  if (firstRowText.toLowerCase().includes('no rows')) {
    throw new Error('No recent games rows found for selected source');
  }
}

async function waitForRecentGamesRowReady(page, maxAttempts = 6) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const rowText = await getRecentGamesRowText(page);
    const lower = rowText.toLowerCase();
    if (!lower.includes('loading') && !lower.includes('no rows')) {
      return;
    }
    await delay(1000);
  }
  throw new Error('Recent games table did not return any rows');
}

module.exports = {
  getTextContent,
  waitForDashboard,
  openRecentGamesTable,
  ensureRecentGamesHasRows,
  waitForRecentGamesRowReady,
};
