const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME || 'dashboard-chesscom-sse-progress.png';

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
  await page.waitForSelector('h1');

  await page.waitForFunction(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const runButton = buttons.find((btn) =>
      btn.textContent?.includes('Run + Refresh'),
    );
    return Boolean(runButton && !runButton.disabled);
  });

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

  await page.waitForFunction(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const runButton = buttons.find((btn) =>
      btn.textContent?.includes('Run + Refresh'),
    );
    return Boolean(runButton && !runButton.disabled);
  });

  await page.$$eval(
    'button',
    (buttons, label) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes(label),
      );
      if (target) target.click();
    },
    'Run + Refresh',
  );

  await page.waitForFunction(() => {
    const headings = Array.from(document.querySelectorAll('h3'));
    return headings.some((heading) =>
      heading.textContent?.includes('Job progress'),
    );
  });

  await page.waitForFunction(() => {
    const listItems = document.querySelectorAll('ol li');
    return listItems.length > 0;
  });

  await new Promise((resolve) => setTimeout(resolve, 1500));

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
