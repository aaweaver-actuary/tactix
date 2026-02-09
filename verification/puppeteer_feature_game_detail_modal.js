const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture, captureScreenshot } = require('./helpers/puppeteer_capture');
const {
  getTextContent,
  waitForDashboard,
  openRecentGamesTable,
  ensureRecentGamesHasRows,
  waitForRecentGamesRowReady,
} = require('./helpers/game_detail_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'lichess';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME || 'feature-game-detail-modal-2026-02-08.png';

const SELECTORS = {
  row: '[data-testid^="recent-games-row-"]',
  modal: '[data-testid="game-detail-modal"]',
  moves: '[data-testid="game-detail-moves"]',
  moveRow: '[data-testid="game-move-row"]',
  analysis: '[data-testid="game-detail-analysis"]',
};

async function openGameDetailModal(page) {
  const rowCellSelector = `${SELECTORS.row} td:first-child`;
  await page.waitForSelector(rowCellSelector);
  await page.click(rowCellSelector);
  await page.waitForSelector(SELECTORS.modal, { visible: true });
  await page.waitForSelector(SELECTORS.moves);
}

async function assertMoveRows(page) {
  const moveRows = await page.$$(SELECTORS.moveRow);
  if (moveRows.length === 0) {
    throw new Error('Expected move list rows in game detail modal');
  }
}

async function assertAnalysisSection(page) {
  const analysisSection = await page.waitForSelector(SELECTORS.analysis);
  const analysisText = await getTextContent(analysisSection);
  const hasEval = analysisText.includes('Eval');
  const hasFlags =
    analysisText.includes('Flags') ||
    analysisText.includes('Blunder') ||
    analysisText.includes('OK');
  if (!hasEval || !hasFlags) {
    throw new Error('Expected analysis section to include eval and blunder checks');
  }
}

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
    await openGameDetailModal(page);
    await assertMoveRows(page);
    await assertAnalysisSection(page);

    const outPath = await captureScreenshot(page, path.resolve(__dirname), SCREENSHOT_NAME);
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
