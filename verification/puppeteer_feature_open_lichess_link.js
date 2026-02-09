const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture, captureScreenshot } = require('./helpers/puppeteer_capture');
const {
  installLichessSpy,
  resetLichessSpy,
  getLichessSpyState,
  waitForLichessUrl,
  assertLichessAnalysisUrl,
} = require('./helpers/lichess_open_helpers');
const {
  openRecentGamesTable,
  ensureRecentGamesHasRows,
  waitForRecentGamesRowReady,
} = require('./helpers/game_detail_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-open-lichess-link-2026-02-08.png';

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const waitWithTimeout = async (promise, timeoutMs, label) => {
  let timeoutId;
  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new Error(`Timed out waiting for ${label}`));
    }, timeoutMs);
  });
  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    clearTimeout(timeoutId);
  }
};

async function waitForDashboard(page) {
  await page.goto(targetUrl, {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await page.waitForSelector('[data-testid="filter-source"]', {
    timeout: 60000,
  });
}

async function setSourceFilter(page, sourceValue) {
  await page.waitForSelector('[data-testid="filter-source"]', {
    timeout: 60000,
  });
  await page.select('[data-testid="filter-source"]', sourceValue);
  await page.waitForFunction(
    (value) => {
      const select = document.querySelector('[data-testid="filter-source"]');
      return select && select.value === value;
    },
    { timeout: 60000 },
    sourceValue,
  );
}

async function getSourceFilterValue(page) {
  return page.evaluate(() => {
    const select = document.querySelector('[data-testid="filter-source"]');
    return select ? select.value : null;
  });
}

async function clickByTestId(page, testId) {
  await page.evaluate((selector) => {
    const target = document.querySelector(selector);
    if (!target) return;
    const event = new MouseEvent('click', {
      bubbles: true,
      cancelable: true,
      view: window,
    });
    target.dispatchEvent(event);
  }, `[data-testid="${testId}"]`);
}

async function captureLichessUrl(page, sourceLabel) {
  try {
    return await waitWithTimeout(
      waitForLichessUrl(page, 15000),
      20000,
      `Lichess URL capture for ${sourceLabel}`,
    );
  } catch (err) {
    const { openCount, lastOpenArgs } = await getLichessSpyState(page);
    throw new Error(
      `No Lichess URL captured for ${sourceLabel}. openCount=${openCount} lastOpenArgs=${lastOpenArgs}`,
    );
  }
}

async function verifyOpenLichessForSource(page, sourceLabel) {
  console.log(`Verifying Open in Lichess for ${sourceLabel}...`);
  await installLichessSpy(page);
  await setSourceFilter(page, sourceLabel);
  const sourceValue = await getSourceFilterValue(page);
  console.log(`Filter source value: ${sourceValue}`);
  await page.waitForSelector('[data-testid="action-run"]', {
    timeout: 60000,
  });
  await page.click('[data-testid="action-run"]');
  await openRecentGamesTable(page);
  await ensureRecentGamesHasRows(page);
  await waitForRecentGamesRowReady(page);
  await page.waitForFunction(
    (label) =>
      Array.from(
        document.querySelectorAll('[data-testid^="recent-games-row-"]'),
      ).some((row) =>
        (row.getAttribute('data-testid') || '').includes(label),
      ),
    { timeout: 20000 },
    sourceLabel,
  );
  const rowTestIds = await page.$$eval(
    '[data-testid^="recent-games-row-"]',
    (rows) => rows.map((row) => row.getAttribute('data-testid') || ''),
  );
  await page.waitForSelector('[data-testid^="open-lichess-"]', {
    timeout: 60000,
  });

  const buttons = await page.$$('[data-testid^="open-lichess-"]');
  if (!buttons.length) {
    throw new Error(`Open in Lichess button missing for ${sourceLabel}`);
  }

  const buttonText = await page.evaluate((btn) => btn.textContent || '', buttons[0]);
  const buttonDisabled = await page.evaluate((btn) => btn.disabled, buttons[0]);
  const buttonTestId = await page.evaluate(
    (btn) => btn.getAttribute('data-testid') || '',
    buttons[0],
  );
  console.log(
    `Found button: ${buttonText.trim()} (disabled=${buttonDisabled}, testid=${buttonTestId})`,
  );

  await resetLichessSpy(page);
  await clickByTestId(page, buttonTestId);
  await delay(500);
  const { openCount: openCountAfterClick } = await getLichessSpyState(page);
  console.log(`window.open call count after click: ${openCountAfterClick}`);
  const url = await captureLichessUrl(page, sourceLabel);
  assertLichessAnalysisUrl(url, `Lichess URL for ${sourceLabel}`);

}

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Navigating to dashboard...');
    await waitForDashboard(page);
    await installLichessSpy(page);

    await verifyOpenLichessForSource(page, 'chesscom');
    await verifyOpenLichessForSource(page, 'lichess');

    const outPath = await captureScreenshot(
      page,
      path.resolve(__dirname),
      SCREENSHOT_NAME,
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
