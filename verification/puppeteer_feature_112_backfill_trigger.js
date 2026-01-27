const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  `feature-112-airflow-backfill-${new Date().toISOString().slice(0, 10)}.png`;

function formatDate(value) {
  return value.toISOString().slice(0, 10);
}

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    protocolTimeout: 120000,
  });
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
    await page.waitForSelector('[data-testid="action-backfill"]');
    await page.waitForSelector('[data-testid="backfill-start"]');
    await page.waitForSelector('[data-testid="backfill-end"]');

    const now = new Date();
    const start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    await page.$eval(
      '[data-testid="backfill-start"]',
      (element, value) => {
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
      },
      formatDate(start),
    );
    await page.$eval(
      '[data-testid="backfill-end"]',
      (element, value) => {
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
      },
      formatDate(now),
    );

    await page.waitForFunction(() => {
      const backfillButton = document.querySelector(
        '[data-testid="action-backfill"]',
      );
      return Boolean(backfillButton && !backfillButton.disabled);
    });

    await page.click('[data-testid="action-backfill"]');

    await page.waitForFunction(
      () => {
        const headings = Array.from(document.querySelectorAll('h3'));
        return headings.some((heading) =>
          heading.textContent?.includes('Job progress'),
        );
      },
      { timeout: 120000 },
    );

    await page.waitForFunction(
      () => {
        const items = Array.from(document.querySelectorAll('ol li'));
        return items.some((item) =>
          item.textContent?.includes('backfill_window'),
        );
      },
      { timeout: 120000 },
    );

    await page.waitForFunction(
      () => {
        const items = Array.from(document.querySelectorAll('ol li'));
        return items.some((item) =>
          item.textContent?.includes('airflow_triggered'),
        );
      },
      { timeout: 120000 },
    );

    await new Promise((resolve) => setTimeout(resolve, 1500));

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('; ')}`);
    }
  } catch (err) {
    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, `failed-${screenshotName}`);
    await page.screenshot({ path: outPath, fullPage: true });
    throw err;
  } finally {
    await browser.close();
  }
})();
