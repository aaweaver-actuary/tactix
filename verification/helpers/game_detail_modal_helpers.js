const { selectSource } = require('../enter_submit_helpers');

async function getTextContent(handle) {
  if (!handle) return '';
  const prop = await handle.getProperty('textContent');
  const value = await prop.jsonValue();
  return value ? String(value) : '';
}

async function waitForDashboard(page, targetUrl, source) {
  await page.goto(targetUrl, { waitUntil: 'networkidle0' });
  await page.waitForSelector('[data-testid="filter-source"]');
  await selectSource(page, source);
  await page.waitForSelector('[data-testid="action-run"]');
  await page.click('[data-testid="action-run"]');
  await new Promise((resolve) => setTimeout(resolve, 2000));
  await page.waitForSelector('[data-testid="dashboard-card-tactics-table"]');
}

async function openRecentGamesTable(page) {
  await page.click('[data-testid="recent-games-card"] [role="button"]');
  await page.waitForSelector('[data-testid="recent-games-card"] table');
}

async function ensureRecentGamesHasRows(page) {
  const firstRow = await page.waitForSelector(
    '[data-testid="recent-games-card"] table tbody tr',
  );
  const firstRowText = await getTextContent(firstRow);
  if (firstRowText.toLowerCase().includes('no rows')) {
    throw new Error('No recent games rows found for selected source');
  }
}

async function waitForRecentGamesRowReady(page, maxAttempts = 6) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const row = await page.waitForSelector(
      '[data-testid="recent-games-card"] table tbody tr',
    );
    const rowText = await getTextContent(row);
    const lower = rowText.toLowerCase();
    if (!lower.includes('loading') && !lower.includes('no rows')) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
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
