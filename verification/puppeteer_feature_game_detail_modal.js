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
    await page.click('[data-testid="recent-games-card"] table tbody tr');
    await page.waitForSelector('[data-testid="game-detail-modal"]', {
      visible: true,
    });
    await page.waitForSelector('[data-testid="game-detail-moves"]');

    const moveRows = await page.$$('[data-testid="game-move-row"]');
    if (moveRows.length === 0) {
      throw new Error('Expected move list rows in game detail modal');
    }

    const analysisSection = await page.waitForSelector(
      '[data-testid="game-detail-analysis"]',
    );
    const analysisText = await getTextContent(analysisSection);
    const hasEval = analysisText.includes('Eval');
    const hasFlags =
      analysisText.includes('Flags') ||
      analysisText.includes('Blunder') ||
      analysisText.includes('OK');
    if (!hasEval || !hasFlags) {
      throw new Error('Expected analysis section to include eval and blunder checks');
    }

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
