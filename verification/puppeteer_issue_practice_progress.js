const puppeteer = require('../client/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');
const {
  selectSource,
  buildFallbackMove,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'issue-practice-progress-2026-02-08.png';
const source = process.env.TACTIX_SOURCE || 'chesscom';
const PRACTICE_CARD_SELECTOR = '[data-testid="dashboard-card-practice-attempt"]';
const PRACTICE_FEEDBACK_LABELS = ['Correct', 'Missed'];
const PRACTICE_ERROR_SNIPPETS = [
  'Enter a move',
  'Illegal move',
  'Failed to submit practice attempt',
];

function parseProgress(summaryText) {
  const match = summaryText.match(/(\d+)\s+of\s+(\d+)\s+attempts/i);
  if (!match) {
    throw new Error(`Unable to parse practice progress from: ${summaryText}`);
  }
  return { completed: Number(match[1]), total: Number(match[2]) };
}

async function getBestMoveFromPracticeCard(page) {
  return page.evaluate((selector) => {
    const card = document.querySelector(selector);
    if (!card) return null;
    const uciPattern = /^[a-h][1-8][a-h][1-8][qrbn]?$/i;
    const spans = Array.from(card.querySelectorAll('span'));
    for (const span of spans) {
      const text = span.textContent?.trim() || '';
      if (!text.startsWith('Best ')) continue;
      const move = text.replace('Best ', '').trim();
      if (uciPattern.test(move)) return move;
    }
    return null;
  }, PRACTICE_CARD_SELECTOR);
}

async function getPracticeFenFromCard(page) {
  return page.evaluate((selector) => {
    const card = document.querySelector(selector);
    if (!card) return null;
    const paragraphs = Array.from(card.querySelectorAll('p'));
    for (let i = 0; i < paragraphs.length; i += 1) {
      const text = paragraphs[i]?.textContent?.trim() || '';
      if (text !== 'FEN') continue;
      const fen = paragraphs[i + 1]?.textContent?.trim() || '';
      return fen || null;
    }
    return null;
  }, PRACTICE_CARD_SELECTOR);
}

async function ensurePracticeCardExpanded(page) {
  const cardSelector = '[data-testid="dashboard-card-practice-attempt"]';
  const headerSelector = `${cardSelector} [role="button"]`;
  await page.waitForSelector(headerSelector, { timeout: 60000 });
  const isCollapsed = await page.$eval(
    headerSelector,
    (header) => header.getAttribute('aria-expanded') === 'false',
  );
  if (isCollapsed) {
    await page.click(headerSelector);
  }
  await page.waitForFunction(
    (selector) => {
      const node = document.querySelector(selector);
      return node && node.getAttribute('data-state') === 'expanded';
    },
    { timeout: 60000 },
    `${cardSelector} [data-state]`,
  );
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = [];
  const practiceRequests = [];
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
  page.on('request', (request) => {
    if (request.url().includes('/api/practice/attempt')) {
      practiceRequests.push(request.url());
    }
  });
  page.on('response', (response) => {
    if (response.url().includes('/api/practice/attempt')) {
      practiceResponses.push(response.status());
    }
  });

  try {
    console.log('Navigating to UI...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await selectSource(page, source);

    await ensurePracticeCardExpanded(page);

    await page.waitForSelector('[data-testid="practice-session-summary"]', {
      timeout: 60000,
    });
    await page.waitForFunction(
      () => {
        const input = document.querySelector('input[placeholder*="UCI"]');
        if (!(input instanceof HTMLInputElement)) return false;
        const visible = input.offsetParent !== null;
        return visible && !input.disabled;
      },
      { timeout: 60000 },
    );
    await page.waitForSelector('input[placeholder*="UCI"]', {
      timeout: 60000,
    });
    await page.waitForFunction(
      (selector) => {
        const fenRegex =
          /^[prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$/;
        const card = document.querySelector(selector);
        if (!card) return false;
        return Array.from(card.querySelectorAll('p')).some((node) =>
          fenRegex.test(node.textContent?.trim() || ''),
        );
      },
      { timeout: 60000 },
      PRACTICE_CARD_SELECTOR,
    );

    const beforeSummary = await page.$eval(
      '[data-testid="practice-session-summary"]',
      (el) => el.textContent || '',
    );
    const before = parseProgress(beforeSummary);
    if (before.total <= 0) {
      throw new Error('Practice session total is zero; queue may be empty.');
    }

    const bestMove = await getBestMoveFromPracticeCard(page);
    const practiceFen = await getPracticeFenFromCard(page);
    if (!practiceFen) {
      throw new Error('Practice FEN not found on the attempt card.');
    }
    const moveToPlay = bestMove || buildFallbackMove(practiceFen);

    console.log(`Submitting practice move: ${moveToPlay}`);
    await page.click('input[placeholder*="UCI"]', { clickCount: 3 });
    await page.keyboard.type(moveToPlay);
    await page.waitForFunction(
      (move) => {
        const input = document.querySelector(
          'input[placeholder*="UCI"]',
        );
        return input && input.value === move;
      },
      { timeout: 60000 },
      moveToPlay,
    );
    await page.keyboard.press('Enter');

    await page.waitForFunction(
      (selector, labels, errors) => {
        const card = document.querySelector(selector);
        if (!card) return false;
        const spans = Array.from(card.querySelectorAll('span'));
        const feedback = spans.some((el) =>
          labels.includes(el.textContent?.trim() || ''),
        );
        const error = Array.from(card.querySelectorAll('p')).some((el) =>
          errors.some((snippet) => (el.textContent || '').includes(snippet)),
        );
        return feedback || error;
      },
      { timeout: 60000 },
      PRACTICE_CARD_SELECTOR,
      PRACTICE_FEEDBACK_LABELS,
      PRACTICE_ERROR_SNIPPETS,
    );

    const result = await page.evaluate((selector, labels, errors) => {
      const card = document.querySelector(selector);
      if (!card) {
        return { feedback: null, error: 'Practice attempt card not found.' };
      }
      const spanText = Array.from(card.querySelectorAll('span'))
        .map((el) => el.textContent?.trim() || '')
        .find((text) => labels.includes(text));
      const errorText = Array.from(card.querySelectorAll('p'))
        .map((el) => el.textContent || '')
        .find(
          (text) => errors.some((snippet) => text.includes(snippet)),
        );
      return { feedback: spanText || null, error: errorText || null };
    }, PRACTICE_CARD_SELECTOR, PRACTICE_FEEDBACK_LABELS, PRACTICE_ERROR_SNIPPETS);

    if (result.error) {
      throw new Error(`Practice submit error: ${result.error}`);
    }

    if (!result.feedback) {
      throw new Error('Expected a graded practice attempt, got none.');
    }

    const afterSummary = await page.$eval(
      '[data-testid="practice-session-summary"]',
      (el) => el.textContent || '',
    );
    const after = parseProgress(afterSummary);

    if (after.total !== before.total) {
      throw new Error(
        `Expected total to stay ${before.total}, got ${after.total}.`,
      );
    }
    if (after.completed !== before.completed + 1) {
      throw new Error(
        `Expected completed to increment from ${before.completed} to ${before.completed + 1}, got ${after.completed}.`,
      );
    }

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });
    console.log('Saved screenshot to', outPath);

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
    if (!practiceRequests.length) {
      console.error('No practice attempt request was detected.');
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
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    if (!practiceRequests.length) {
      console.error('No practice attempt request was detected.');
    } else {
      console.error('Practice attempt response statuses:', practiceResponses);
    }
    console.error('Practice progress verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
