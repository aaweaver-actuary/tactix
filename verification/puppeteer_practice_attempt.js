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
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'dashboard-practice-attempt-grading.png';
const source = process.env.TACTIX_SOURCE || 'chesscom';

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = [];
  const practiceResponses = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(err.toString()));
  page.on('requestfailed', (request) => {
    consoleErrors.push(
      `Request failed: ${request.url()} (${request.failure()?.errorText || 'unknown'})`,
    );
  });
  page.on('response', async (response) => {
    if (!response.url().includes('/api/practice/attempt')) return;
    if (response.request().method() !== 'POST') return;
    try {
      const payload = await response.json();
      practiceResponses.push(payload);
    } catch (err) {
      console.error('Practice attempt response parse failed:', err);
    }
  });

  try {
    console.log('Navigating to UI...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1');
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

    await page.waitForSelector('h3', { timeout: 60000 });
    await new Promise((resolve) => setTimeout(resolve, 2000));
    await page.waitForSelector('[data-testid="practice-start"]', {
      timeout: 60000,
    });
    await page.click('[data-testid="practice-start"]');
    await page.waitForSelector('[data-testid="chessboard-modal"]', {
      timeout: 60000,
    });
    await page.waitForFunction(
      () => {
        const modal = document.querySelector(
          '[data-testid="chessboard-modal"]',
        );
        const input = modal?.querySelector('input[placeholder*="UCI"]');
        if (!(input instanceof HTMLInputElement)) return false;
        const visible = input.offsetParent !== null;
        return visible && !input.disabled;
      },
      { timeout: 60000 },
    );
    let input;
    try {
      input = await page.waitForSelector(
        '[data-testid="chessboard-modal"] input[placeholder*="UCI"]',
        {
          timeout: 60000,
        },
      );
    } catch (err) {
      const placeholders = await page.$$eval('input', (inputs) =>
        inputs.map((inputEl) => inputEl.getAttribute('placeholder')),
      );
      console.error('Available input placeholders:', placeholders);
      throw err;
    }
    if (!input) {
      throw new Error('Practice attempt input not found (queue may be empty).');
    }

    const bestLabel = await page.$eval(
      '[data-testid="chessboard-modal"]',
      (modal) => {
        const spans = Array.from(modal.querySelectorAll('span'));
        const best = spans.find((span) =>
          span.textContent?.startsWith('Best '),
        );
        return best?.textContent || '';
      },
    );
    const rawBestMove = bestLabel.replace('Best ', '').trim();
    const bestMove = rawBestMove && rawBestMove !== '--' ? rawBestMove : 'e2e4';

    const beforeSummary = await page.$eval(
      '[data-testid="practice-session-summary"]',
      (el) => el.textContent || '',
    );
    const beforeMatch = beforeSummary.match(/(\d+)\s+of\s+(\d+)\s+attempts/i);
    const beforeTotal = beforeMatch ? Number(beforeMatch[2]) : null;

    const fen = await getFenFromPage(page);
    const board = new Chess(fen);
    const moves = board.moves({ verbose: true });
    const bestUci = bestMove.toLowerCase();
    const altMove = moves
      .map((move) => `${move.from}${move.to}${move.promotion || ''}`)
      .find((uci) => uci !== bestUci);
    if (!altMove) {
      throw new Error(
        'Unable to find a legal non-best move for reschedule test.',
      );
    }

    const inputSelector =
      '[data-testid="chessboard-modal"] input[placeholder*="UCI"]';
    const submitSelector = 'button';

    await page.click(inputSelector, { clickCount: 3 });
    await page.keyboard.type(altMove);
    await page.$$eval(submitSelector, (buttons) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes('Submit attempt'),
      );
      if (target) target.click();
    });
    await page.waitForFunction(
      () =>
        Array.from(document.querySelectorAll('span')).some((el) =>
          el.textContent?.includes('Missed'),
        ),
      { timeout: 60000 },
    );
    if (beforeTotal !== null) {
      await page.waitForFunction(
        (selector, prevTotal) => {
          const el = document.querySelector(selector);
          if (!el) return false;
          const match = (el.textContent || '').match(
            /(\d+)\s+of\s+(\d+)\s+attempts/i,
          );
          if (!match) return false;
          const total = Number(match[2]);
          return Number.isFinite(total) && total > prevTotal;
        },
        { timeout: 60000 },
        '[data-testid="practice-session-summary"]',
        beforeTotal,
      );
      const afterSummary = await page.$eval(
        '[data-testid="practice-session-summary"]',
        (el) => el.textContent || '',
      );
      const afterMatch = afterSummary.match(/(\d+)\s+of\s+(\d+)\s+attempts/i);
      const afterTotal = afterMatch ? Number(afterMatch[2]) : null;
      if (afterTotal !== null && afterTotal <= beforeTotal) {
        throw new Error('Expected practice total to increase after a miss.');
      }
    }

    await page.click(inputSelector, { clickCount: 3 });
    await page.keyboard.type(bestMove);
    await page.$$eval(submitSelector, (buttons) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes('Submit attempt'),
      );
      if (target) target.click();
    });

    await page.waitForSelector('span', { timeout: 60000 });
    await new Promise((resolve) => setTimeout(resolve, 1500));

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });
    console.log('Saved screenshot to', outPath);

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
  } catch (err) {
    try {
      const outDir = path.resolve(__dirname);
      fs.mkdirSync(outDir, { recursive: true });
      const outPath = path.join(outDir, `failed-${screenshotName}`);
      await page.screenshot({ path: outPath, fullPage: true });
      console.error('Saved failure screenshot to', outPath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (practiceResponses.length) {
      console.error('Practice attempt responses:', practiceResponses);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Practice attempt verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
