const puppeteer = require('../client/node_modules/puppeteer');
const { Chess } = require('../client/node_modules/chess.js');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME || 'ui-enter-submit-2026-02-08.png';
const source = process.env.TACTIX_SOURCE || 'chesscom';
const logName =
  process.env.TACTIX_LOG_NAME || 'tmp-logs/ui-enter-submit-2026-02-08.json';

async function selectSource(page) {
  if (source !== 'chesscom') return;
  try {
    await page.waitForFunction(
      () => {
        const el = document.querySelector(
          'select[data-testid="filter-source"]',
        );
        return el && !el.disabled;
      },
      { timeout: 60000 },
    );
    await page.select('select[data-testid="filter-source"]', 'chesscom');
  } catch (err) {
    await page.$$eval(
      'button',
      (buttons, label) => {
        const target = buttons.find(
          (btn) => btn.textContent && btn.textContent.includes(label),
        );
        if (target) target.click();
      },
      'Chess.com',
    );
  }
}

async function getBestMoveFromPage(page) {
  const bestLabel = await page.$$eval('span', (spans) => {
    const best = spans.find((span) => {
      const text = span.textContent?.trim() || '';
      return text.startsWith('Best ') && text !== 'Best --';
    });
    return best?.textContent || '';
  });

  const rawBestMove = bestLabel.replace('Best ', '').trim();
  if (!rawBestMove || rawBestMove === '--') {
    return null;
  }
  return rawBestMove;
}

async function getFenFromPage(page) {
  const fen = await page.$$eval('p', (nodes) => {
    const fenRegex =
      /^[prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$/;
    const match = nodes
      .map((node) => node.textContent?.trim() || '')
      .find((text) => fenRegex.test(text));
    return match || '';
  });
  if (!fen) {
    throw new Error('Practice FEN not found for fallback move.');
  }
  return fen;
}

function buildFallbackMove(fen) {
  const board = new Chess(fen);
  const moves = board.moves({ verbose: true });
  if (!moves.length) {
    throw new Error('No legal moves available for fallback.');
  }
  const move = moves[0];
  return `${move.from}${move.to}${move.promotion || ''}`;
}

function ensureDir(filePath) {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = [];
  const logPayload = {
    screenshot: null,
    log: null,
    submittedMove: null,
    bestMoveFromPage: null,
    fallbackFen: null,
    fallbackMove: null,
    feedback: null,
    errors: [],
  };

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
    await page.waitForSelector('h1');
    await selectSource(page);

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
    const inputSelector = 'input[placeholder*="UCI"]';
    const input = await page.waitForSelector(inputSelector, { timeout: 60000 });
    if (!input) {
      throw new Error('Practice attempt input not found (queue may be empty).');
    }

    const bestMoveFromPage = await getBestMoveFromPage(page);
    let bestMove = bestMoveFromPage;
    if (!bestMove || bestMove.trim().length < 4) {
      const fallbackFen = await getFenFromPage(page);
      bestMove = buildFallbackMove(fallbackFen);
      logPayload.fallbackFen = fallbackFen;
      logPayload.fallbackMove = bestMove;
    } else {
      logPayload.bestMoveFromPage = bestMove;
    }
    logPayload.submittedMove = bestMove;

    await page.click(inputSelector, { clickCount: 3 });
    await page.keyboard.type(bestMove);
    await page.keyboard.press('Enter');

    await page.waitForFunction(
      () => {
        const spans = Array.from(document.querySelectorAll('span'));
        const feedback = spans.some((el) =>
          ['Correct', 'Missed'].includes(el.textContent?.trim() || ''),
        );
        const error = Array.from(document.querySelectorAll('p')).some((el) =>
          (el.textContent || '').includes('Enter a move') ||
          (el.textContent || '').includes('Illegal move') ||
          (el.textContent || '').includes('Failed to submit practice attempt'),
        );
        return feedback || error;
      },
      { timeout: 60000 },
    );

    const result = await page.evaluate(() => {
      const spanText = Array.from(document.querySelectorAll('span'))
        .map((el) => el.textContent?.trim() || '')
        .find((text) => ['Correct', 'Missed'].includes(text));
      const errorText = Array.from(document.querySelectorAll('p'))
        .map((el) => el.textContent || '')
        .find(
          (text) =>
            text.includes('Enter a move') ||
            text.includes('Illegal move') ||
            text.includes('Failed to submit practice attempt'),
        );
      return { feedback: spanText || null, error: errorText || null };
    });

    if (result.error) {
      throw new Error(`Practice submit error: ${result.error}`);
    }
    logPayload.feedback = result.feedback;

    const screenshotPath = path.join(__dirname, screenshotName);
    ensureDir(screenshotPath);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log('Saved screenshot to', screenshotPath);
    logPayload.screenshot = screenshotPath;

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      logPayload.errors = consoleErrors;
      throw new Error('Console errors detected during verification.');
    }
  } catch (err) {
    logPayload.errors = logPayload.errors.concat(consoleErrors);
    try {
      const failurePath = path.join(__dirname, `failed-${screenshotName}`);
      ensureDir(failurePath);
      await page.screenshot({ path: failurePath, fullPage: true });
      console.error('Saved failure screenshot to', failurePath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    console.error('Enter submit verification failed:', err);
    throw err;
  } finally {
    const logPath = path.resolve(__dirname, '..', logName);
    logPayload.log = logPath;
    ensureDir(logPath);
    fs.writeFileSync(logPath, JSON.stringify(logPayload, null, 2));
    await browser.close();
  }
})();
