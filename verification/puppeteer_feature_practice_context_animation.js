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
const source = process.env.TACTIX_SOURCE || 'chesscom';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-practice-context-animation-2026-02-10.png';

const selectors = {
  practiceButton: '[data-testid="practice-button"]',
  practiceModal: '[data-testid="chessboard-modal"]',
  practiceMoveInput: '[data-testid="chessboard-modal"] input[placeholder*="UCI"]',
  practiceBoardPanel: '.practice-context-board',
  practiceDetails: '.practice-context-details',
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('h1', { timeout: 60000 });
    await selectSource(page, source);
    await ensurePracticeCardExpanded(page);

    await page.waitForSelector(selectors.practiceButton, { timeout: 60000 });
    await page.waitForFunction(
      (selector) => {
        const button = document.querySelector(selector);
        if (!button) return false;
        return !(button.textContent || '').includes('Loading practice...');
      },
      { timeout: 60000 },
      selectors.practiceButton,
    );
    try {
      await page.waitForFunction(
        (selector) => {
          const button = document.querySelector(selector);
          return button instanceof HTMLButtonElement && !button.disabled;
        },
        { timeout: 60000 },
        selectors.practiceButton,
      );
    } catch {
      const buttonState = await page.$eval(
        selectors.practiceButton,
        (button) => ({
          disabled: button instanceof HTMLButtonElement && button.disabled,
          label: button.textContent?.trim() || '',
        }),
      );
      throw new Error(
        `Practice button is disabled; need practice items (label: "${buttonState.label}").`,
      );
    }
    await page.click(selectors.practiceButton);
    await page.waitForSelector(selectors.practiceModal, { timeout: 60000 });
    await page.waitForSelector(selectors.practiceMoveInput, { timeout: 60000 });
    await page.waitForSelector(selectors.practiceBoardPanel, { timeout: 60000 });

    await page.click(selectors.practiceMoveInput, { clickCount: 3 });
    await page.keyboard.type('e2e4');

    const typedValue = await page.$eval(
      selectors.practiceMoveInput,
      (input) => (input instanceof HTMLInputElement ? input.value : ''),
    );
    if (!typedValue.includes('e2e4')) {
      throw new Error('Practice input did not accept typing during animation.');
    }

    const animationNames = await page.evaluate(
      (boardSelector, detailsSelector) => {
        const reduced = window.matchMedia(
          '(prefers-reduced-motion: reduce)',
        ).matches;
        const board = document.querySelector(boardSelector);
        const details = document.querySelector(detailsSelector);
        const boardStyle = board ? window.getComputedStyle(board) : null;
        const detailsStyle = details ? window.getComputedStyle(details) : null;
        return {
          reduced,
          board: boardStyle?.animationName || '',
          details: detailsStyle?.animationName || '',
        };
      },
      selectors.practiceBoardPanel,
      selectors.practiceDetails,
    );

    if (!animationNames.reduced) {
      if (!animationNames.board.includes('practiceContextRise')) {
        throw new Error('Practice board context animation is missing.');
      }
      if (!animationNames.details.includes('practiceContextRise')) {
        throw new Error('Practice details context animation is missing.');
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 200));
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
