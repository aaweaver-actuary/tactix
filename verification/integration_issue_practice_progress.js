const puppeteer = require('../client/node_modules/puppeteer');
const {
  selectSource,
  buildFallbackMove,
  ensurePracticeCardExpanded,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const source = process.env.TACTIX_SOURCE || 'chesscom';

function parseProgress(summaryText) {
  const match = summaryText.match(/(\d+)\s+of\s+(\d+)\s+attempts/i);
  if (!match) {
    throw new Error(`Unable to parse practice progress from: ${summaryText}`);
  }
  return { completed: Number(match[1]), total: Number(match[2]) };
}

async function getBestMoveFromPracticeCard(page) {
  return page.evaluate(() => {
    const modal = document.querySelector('[data-testid="chessboard-modal"]');
    const scope = modal || document;
    const uciPattern = /^[a-h][1-8][a-h][1-8][qrbn]?$/i;
    const spans = Array.from(scope.querySelectorAll('span'));
    for (const span of spans) {
      const text = span.textContent?.trim() || '';
      if (!text.startsWith('Best ')) continue;
      const move = text.replace('Best ', '').trim();
      if (uciPattern.test(move)) return move;
    }
    return null;
  });
}

async function getPracticeFenFromCard(page) {
  return page.evaluate(() => {
    const modal = document.querySelector('[data-testid="chessboard-modal"]');
    const scope = modal || document;
    const paragraphs = Array.from(scope.querySelectorAll('p'));
    for (let i = 0; i < paragraphs.length; i += 1) {
      const text = paragraphs[i]?.textContent?.trim() || '';
      if (text !== 'FEN') continue;
      const fen = paragraphs[i + 1]?.textContent?.trim() || '';
      return fen || null;
    }
    return null;
  });
}

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
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await selectSource(page, source);
    await ensurePracticeCardExpanded(page);

    await page.waitForSelector('[data-testid="practice-session-summary"]', {
      timeout: 60000,
    });
    await page.waitForSelector('[data-testid="practice-start"]', {
      timeout: 60000,
    });
    await page.click('[data-testid="practice-start"]');
    await page.waitForSelector('[data-testid="chessboard-modal"]', {
      timeout: 60000,
    });
    await page.waitForSelector('input[placeholder*="UCI"]', {
      timeout: 60000,
    });
    await page.waitForFunction(
      () => {
        const fenRegex =
          /^[prnbqkPRNBQK1-8\/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$/;
        return Array.from(document.querySelectorAll('p')).some((node) =>
          fenRegex.test(node.textContent?.trim() || ''),
        );
      },
      { timeout: 60000 },
    );

    const beforeSummary = await page.$eval(
      '[data-testid="practice-session-summary"]',
      (el) => el.textContent || '',
    );
    const before = parseProgress(beforeSummary);
    console.log('Practice summary before:', beforeSummary);

    const bestMove = await getBestMoveFromPracticeCard(page);
    const practiceFen = await getPracticeFenFromCard(page);
    if (!practiceFen) {
      throw new Error('Practice FEN not found on the attempt card.');
    }
    const moveToPlay = bestMove || buildFallbackMove(practiceFen);

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
    await page.$$eval('button', (buttons) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes('Submit attempt'),
      );
      if (target) target.click();
    });

    await page.waitForFunction(
      () => {
        const spans = Array.from(document.querySelectorAll('span'));
        const feedback = spans.some((el) =>
          ['Correct', 'Missed'].includes(el.textContent?.trim() || ''),
        );
        const error = Array.from(document.querySelectorAll('p')).some(
          (el) =>
            (el.textContent || '').includes('Enter a move') ||
            (el.textContent || '').includes('Illegal move') ||
            (el.textContent || '').includes(
              'Failed to submit practice attempt',
            ),
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

    if (!result.feedback) {
      throw new Error('Expected a graded practice attempt, got none.');
    }

    const practiceResult = practiceResponses[0];
    if (!practiceResult) {
      throw new Error('Practice attempt response was not captured.');
    }
    const shouldReschedule =
      practiceResult.rescheduled ?? practiceResult.correct === false;

    const afterSummary = await page.$eval(
      '[data-testid="practice-session-summary"]',
      (el) => el.textContent || '',
    );
    const after = parseProgress(afterSummary);
    console.log('Practice summary after:', afterSummary);

    const expectedTotal = before.total + (shouldReschedule ? 1 : 0);
    if (after.total !== expectedTotal) {
      throw new Error(
        `Expected total to be ${expectedTotal}, got ${after.total}.`,
      );
    }
    if (after.completed !== before.completed + 1) {
      throw new Error(
        `Expected completed to increment from ${before.completed} to ${before.completed + 1}, got ${after.completed}.`,
      );
    }

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Practice progress increment integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
