const { selectSource } = require('../enter_submit_helpers');
const { closeFiltersModal } = require('./filters_modal_helpers');

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function getTextContent(handle) {
  if (!handle) return '';
  const prop = await handle.getProperty('textContent');
  const value = await prop.jsonValue();
  return value ? String(value) : '';
}

const SELECTORS = {
  dashboardReady: 'h1',
  fabToggle: '[data-testid="fab-toggle"]',
  recentGamesOpen: '[data-testid="recent-games-open"]',
  recentGamesModal: '[data-testid="recent-games-modal"]',
  recentGamesRow: '[data-testid^="recent-games-row-"]',
};

async function waitForDashboard(page, targetUrl, source) {
  await page.goto(targetUrl, { waitUntil: 'networkidle0' });
  await page.waitForSelector(SELECTORS.dashboardReady, { timeout: 60000 });
  await selectSource(page, source);
  await page.waitForSelector(SELECTORS.fabToggle, { timeout: 60000 });
}

async function getRecentGamesRowText(page) {
  const row = await page.waitForSelector(SELECTORS.recentGamesRow);
  return getTextContent(row);
}

async function openRecentGamesTable(page) {
  await closeFiltersModal(page);
  await page.waitForSelector(SELECTORS.fabToggle, { timeout: 60000 });
  await page.click(SELECTORS.fabToggle);
  await page.waitForSelector(SELECTORS.recentGamesOpen, { timeout: 60000 });
  await page.click(SELECTORS.recentGamesOpen);
  await page.waitForSelector(SELECTORS.recentGamesModal, { timeout: 60000 });
  await page.waitForSelector(SELECTORS.recentGamesRow, { timeout: 60000 });
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
