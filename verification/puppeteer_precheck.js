const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME || 'precheck-dashboard.png';
const source = process.env.TACTIX_SOURCE || 'lichess';
const actionLabel = process.env.TACTIX_ACTION_LABEL || 'Run + Refresh';

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

  await page.goto(targetUrl, { waitUntil: 'networkidle0' });
  await page.waitForSelector('[data-testid="filter-source"]');

  if (source === 'chesscom') {
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

  await page.$$eval(
    'button',
    (buttons, label) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes(label),
      );
      if (target) target.click();
    },
    actionLabel,
  );

  await page.waitForSelector('table');
  await new Promise((resolve) => setTimeout(resolve, 2000));

  const outDir = path.resolve(__dirname);
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, screenshotName);
  await page.screenshot({ path: outPath, fullPage: true });

  await browser.close();

  if (consoleErrors.length) {
    console.error('Console errors detected:', consoleErrors);
    process.exit(1);
  }
})();
