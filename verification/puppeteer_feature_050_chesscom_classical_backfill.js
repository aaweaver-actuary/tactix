const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-050-chesscom-classical-backfill-2026-01-25.png';

const getMetricValue = async (page, title) => {
  return page.$$eval(
    'div.card',
    (cards, label) => {
      const match = cards.find((card) => {
        const titleEl =
          card.querySelector('p.text-sm') || card.querySelector('p.text-xs');
        return titleEl && titleEl.textContent?.trim() === label;
      });
      if (!match) return null;
      const valueEl = match.querySelector('p.text-3xl');
      return valueEl ? valueEl.textContent?.trim() : null;
    },
    title,
  );
};

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
    await page.goto(targetUrl, { waitUntil: 'networkidle0', timeout: 60000 });
    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: 60000,
    });
    await page.waitForFunction(
      () => !document.querySelector('[data-testid="filter-source"]')?.disabled,
      { timeout: 60000 },
    );

    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]', {
      timeout: 60000,
    });
    await page.select('[data-testid="filter-chesscom-profile"]', 'classical');

    await page.waitForSelector('[data-testid="action-backfill"]', {
      timeout: 60000,
    });

    const positionsBefore = await getMetricValue(page, 'Positions');
    const tacticsBefore = await getMetricValue(page, 'Tactics');

    await page.click('[data-testid="action-backfill"]');
    await page.waitForSelector(
      '[data-testid="action-backfill"]:not([disabled])',
      { timeout: 180000 },
    );
    await page.waitForSelector('[data-testid="motif-breakdown"]', {
      timeout: 120000,
    });
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const positionsAfterFirst = await getMetricValue(page, 'Positions');
    const tacticsAfterFirst = await getMetricValue(page, 'Tactics');

    await page.click('[data-testid="action-backfill"]');
    await page.waitForSelector(
      '[data-testid="action-backfill"]:not([disabled])',
      { timeout: 180000 },
    );
    await page.waitForSelector('[data-testid="motif-breakdown"]', {
      timeout: 120000,
    });
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const positionsAfterSecond = await getMetricValue(page, 'Positions');
    const tacticsAfterSecond = await getMetricValue(page, 'Tactics');

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });

    if (
      positionsAfterFirst !== positionsAfterSecond ||
      tacticsAfterFirst !== tacticsAfterSecond
    ) {
      throw new Error(
        `Backfill changed counts between runs: positions ${positionsAfterFirst} -> ${positionsAfterSecond}, ` +
          `tactics ${tacticsAfterFirst} -> ${tacticsAfterSecond}`,
      );
    }

    if (positionsBefore === null || tacticsBefore === null) {
      throw new Error('Unable to read Positions/Tactics metrics');
    }

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
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Feature 050 verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
