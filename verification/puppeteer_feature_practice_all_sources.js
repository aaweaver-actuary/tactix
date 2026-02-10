const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const {
  selectSource,
  ensurePracticeCardExpanded,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-practice-all-sources-2026-02-10.png';

const selectors = {
  practiceButton: '[data-testid="practice-button"]',
  practiceStatus: '[data-testid="practice-button-status"]',
  practiceQueueRow: '[data-testid^="practice-queue-row-"]',
};

const allowedDisabledLabels = [
  'No practice items',
  'Practice complete',
  'Practice unavailable',
  'Loading practice...',
];

const parsePracticeReadyCount = (statusText) => {
  const match = statusText.match(/(\d+)\s+tactic/i);
  return match ? Number(match[1]) : null;
};

async function loadPracticeState(page, source, previousStatus) {
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

  const queueCount = await page.$$eval(
    selectors.practiceQueueRow,
    (rows) => rows.length,
  );
  const statusText = await page.$eval(
    selectors.practiceStatus,
    (node) => node.textContent?.trim() || '',
  );
  const buttonState = await page.$eval(selectors.practiceButton, (button) => ({
    disabled: button instanceof HTMLButtonElement && button.disabled,
    label: button.textContent?.trim() || '',
  }));

  return { queueCount, statusText, buttonState };
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1', { timeout: 60000 });

    const chesscomState = await loadPracticeState(page, 'chesscom', null);
    const allState = await loadPracticeState(
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

    const allStatusCount = parsePracticeReadyCount(allState.statusText);
    if (allState.queueCount > 0) {
      if (allState.buttonState.disabled) {
        throw new Error('Practice button should be enabled for all sources.');
      }
      if (allStatusCount !== null && allStatusCount !== allState.queueCount) {
        throw new Error(
          `Practice status count ${allStatusCount} should match queue count ${allState.queueCount}.`,
        );
      }
    } else {
      if (!allState.buttonState.disabled) {
        throw new Error(
          'Practice button should be disabled when no all-source items exist.',
        );
      }
      if (
        !allowedDisabledLabels.some((label) =>
          allState.buttonState.label.includes(label),
        )
      ) {
        throw new Error(
          `Unexpected practice button label for all sources: "${allState.buttonState.label}"`,
        );
      }
    }

    const outPath = await captureScreenshot(
      page,
      path.resolve(__dirname),
      screenshotName,
    );
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
