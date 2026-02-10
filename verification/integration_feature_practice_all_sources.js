const puppeteer = require('../client/node_modules/puppeteer');
const {
  selectSource,
  ensurePracticeCardExpanded,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';

const selectors = {
  practiceButton: '[data-testid="practice-button"]',
  practiceStatus: '[data-testid="practice-button-status"]',
  practiceQueueRow: '[data-testid^="practice-queue-row-"]',
};

async function readPracticeState(page, source, previousStatus) {
  await selectSource(page, source);
  await ensurePracticeCardExpanded(page);
  await page.waitForSelector(selectors.practiceButton, { timeout: 60000 });
  await page.waitForSelector(selectors.practiceStatus, { timeout: 60000 });
  if (previousStatus !== null) {
    await page.waitForFunction(
      (selector, prior) => {
        const text = document.querySelector(selector)?.textContent || '';
        return text.trim() !== prior.trim();
      },
      { timeout: 60000 },
      selectors.practiceStatus,
      previousStatus,
    );
  }

  return page.evaluate((stateSelectors) => {
    const queueCount = document.querySelectorAll(
      stateSelectors.practiceQueueRow,
    ).length;
    const statusText =
      document.querySelector(stateSelectors.practiceStatus)?.textContent?.trim() ||
      '';
    const button = document.querySelector(stateSelectors.practiceButton);
    const disabled =
      button instanceof HTMLButtonElement ? button.disabled : true;
    return { queueCount, statusText, disabled };
  }, selectors);
}

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
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });

    const chesscomState = await readPracticeState(page, 'chesscom', null);
    const allState = await readPracticeState(
      page,
      'all',
      chesscomState.statusText,
    );

    if (chesscomState.queueCount > 0 && allState.queueCount === 0) {
      throw new Error(
        'All sources should surface practice items when chess.com has items.',
      );
    }
    if (allState.queueCount < chesscomState.queueCount) {
      throw new Error(
        `All sources should include chess.com items (chesscom=${chesscomState.queueCount}, all=${allState.queueCount}).`,
      );
    }
    if (allState.queueCount > 0 && allState.disabled) {
      throw new Error('Practice button should be enabled for all sources.');
    }

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('All-sources practice availability integration verified.');
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
