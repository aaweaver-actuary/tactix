const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const { attachConsoleCapture, captureScreenshot } = require('./helpers/puppeteer_capture');
const {
  openRecentGamesTable,
  ensureRecentGamesHasRows,
  waitForRecentGamesRowReady,
} = require('./helpers/game_detail_modal_helpers');
const { selectSource } = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-open-lichess-link-2026-02-08.png';

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

async function installLichessSpy(page) {
  await page.evaluate(() => {
    window.__lastLichessUrl = null;
    window.__lastOpenArgs = null;
    window.__openCallCount = 0;
    window.open = (url) => {
      window.__openCallCount += 1;
      window.__lastOpenArgs = url || null;
      if (url && url !== 'about:blank') {
        window.__lastLichessUrl = url;
      }
      return {
        close() {},
        opener: null,
        location: {
          set href(nextUrl) {
            if (nextUrl) window.__lastLichessUrl = nextUrl;
          },
        },
      };
    };
  });
}

async function waitForDashboard(page) {
  await page.goto(targetUrl, {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await page.waitForSelector('[data-testid="filter-source"]', {
    timeout: 60000,
  });
}

async function verifyOpenLichessForSource(page, sourceLabel) {
  console.log(`Verifying Open in Lichess for ${sourceLabel}...`);
  await installLichessSpy(page);
  await selectSource(page, sourceLabel);
  const sourceValue = await page.evaluate(() => {
    const select = document.querySelector('[data-testid="filter-source"]');
    return select ? select.value : null;
  });
  console.log(`Filter source value: ${sourceValue}`);
  await page.waitForSelector('[data-testid="action-run"]', {
    timeout: 60000,
  });
  await page.click('[data-testid="action-run"]');
  await openRecentGamesTable(page);
  await ensureRecentGamesHasRows(page);
  await waitForRecentGamesRowReady(page);
  const rowTestIds = await page.$$eval(
    '[data-testid^="recent-games-row-"]',
    (rows) => rows.map((row) => row.getAttribute('data-testid') || ''),
  );
  const hasSourceRow = rowTestIds.some((id) => id.includes(sourceLabel));
  if (!hasSourceRow) {
    throw new Error(
      `Recent games rows did not include source ${sourceLabel}. Found: ${rowTestIds.join(', ')}`,
    );
  }
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

  await page.evaluate(() => {
    window.__lastLichessUrl = null;
    window.__lastOpenArgs = null;
    window.__openCallCount = 0;
  });
  await page.evaluate((selector) => {
    const target = document.querySelector(selector);
    if (!target) return;
    const event = new MouseEvent('click', {
      bubbles: true,
      cancelable: true,
      view: window,
    });
    target.dispatchEvent(event);
  }, `[data-testid="${buttonTestId}"]`);
  await new Promise((resolve) => setTimeout(resolve, 500));
  const openCountAfterClick = await page.evaluate(
    () => window.__openCallCount || 0,
  );
  console.log(`window.open call count after click: ${openCountAfterClick}`);
  let url = '';
  try {
    await waitWithTimeout(
      page.waitForFunction(() => Boolean(window.__lastLichessUrl), {
        timeout: 15000,
      }),
      20000,
      `Lichess URL capture for ${sourceLabel}`,
    );
    url = await page.evaluate(() => window.__lastLichessUrl || '');
  } catch (err) {
    const openCount = await page.evaluate(() => window.__openCallCount || 0);
    const lastOpenArgs = await page.evaluate(() => window.__lastOpenArgs || '');
    throw new Error(
      `No Lichess URL captured for ${sourceLabel}. openCount=${openCount} lastOpenArgs=${lastOpenArgs}`,
    );
  }

  if (!url.startsWith('https://lichess.org/analysis/pgn/')) {
    throw new Error(`Unexpected Lichess URL for ${sourceLabel}: ${url}`);
  }
  if (!url.includes('?color=')) {
    throw new Error(`Missing color param for ${sourceLabel}: ${url}`);
  }
  if (!url.includes('#')) {
    throw new Error(`Missing move anchor for ${sourceLabel}: ${url}`);
  }

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
