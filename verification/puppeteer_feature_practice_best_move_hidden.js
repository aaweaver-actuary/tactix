const puppeteer = require('../client/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');
const { Chess } = require('../client/node_modules/chess.js');
const {
  selectSource,
  getFenFromPage,
  ensurePracticeCardExpanded,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'chesscom';
const beforeScreenshot =
  process.env.TACTIX_SCREENSHOT_BEFORE ||
  'feature-practice-best-move-hidden-before-2026-02-10.png';
const afterScreenshot =
  process.env.TACTIX_SCREENSHOT_AFTER ||
  'feature-practice-best-move-hidden-after-2026-02-10.png';

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
    console.log('Navigating to UI...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await selectSource(page, source);
    await ensurePracticeCardExpanded(page);

    console.log('Refreshing metrics to load practice queue...');
    await page.$$eval(
      'button',
      (buttons, label) => {
        const target = buttons.find(
          (btn) => btn.textContent && btn.textContent.includes(label),
        );
        if (target) target.click();
      },
      'Refresh metrics',
    );

    await page.waitForSelector('[data-testid="practice-start"]', {
      timeout: 60000,
    });
    await page.click('[data-testid="practice-start"]');
    await page.waitForSelector('[data-testid="chessboard-modal"]', {
      timeout: 60000,
    });
    await page.waitForFunction(
      () => {
        const modal = document.querySelector('[data-testid="chessboard-modal"]');
        const input = modal?.querySelector('input[placeholder*="UCI"]');
        if (!(input instanceof HTMLInputElement)) return false;
        const visible = input.offsetParent !== null;
        return visible && !input.disabled;
      },
      { timeout: 60000 },
    );

    const preAttemptBestBadge = await page.$(
      '[data-testid="chessboard-modal"] [data-testid="practice-best-move"]',
    );
    if (preAttemptBestBadge) {
      throw new Error('Best move badge should be hidden before attempting.');
    }

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const beforePath = path.join(outDir, beforeScreenshot);
    await page.screenshot({ path: beforePath, fullPage: true });
    console.log('Saved screenshot to', beforePath);

    const fen = await getFenFromPage(page);
    const board = new Chess(fen);
    const attemptMove = board
      .moves({ verbose: true })
      .map((move) => `${move.from}${move.to}${move.promotion || ''}`)
      .find(Boolean);
    if (!attemptMove) {
      throw new Error('Unable to find a legal move for practice attempt.');
    }

    const inputSelector =
      '[data-testid="chessboard-modal"] input[placeholder*="UCI"]';
    await page.click(inputSelector, { clickCount: 3 });
    await page.keyboard.type(attemptMove);
    await page.$$eval('button', (buttons) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes('Submit attempt'),
      );
      if (target) target.click();
    });

    await page.waitForFunction(
      () =>
        Array.from(document.querySelectorAll('span')).some((el) =>
          ['Correct', 'Missed'].some((label) =>
            el.textContent?.includes(label),
          ),
        ),
      { timeout: 60000 },
    );
    await page.waitForSelector('[data-testid="practice-best-move"]', {
      timeout: 60000,
    });

    const afterPath = path.join(outDir, afterScreenshot);
    await page.screenshot({ path: afterPath, fullPage: true });
    console.log('Saved screenshot to', afterPath);

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
  } catch (err) {
    try {
      const outDir = path.resolve(__dirname);
      fs.mkdirSync(outDir, { recursive: true });
      const outPath = path.join(outDir, `failed-${afterScreenshot}`);
      await page.screenshot({ path: outPath, fullPage: true });
      console.error('Saved failure screenshot to', outPath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Practice best move verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
