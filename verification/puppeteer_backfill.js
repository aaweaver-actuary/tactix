const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME || 'dashboard-lichess-backfill.png';
const source = process.env.TACTIX_SOURCE || 'lichess';

const getMetricValue = async (page, title) => {
  return page.$$eval(
    'div.card',
    (cards, label) => {
      const match = cards.find((card) => {
        const titleEl = card.querySelector('p.text-sm');
        return titleEl && titleEl.textContent?.trim() === label;
      });
      if (!match) return null;
      const valueEl = match.querySelector('p.text-3xl');
      return valueEl ? valueEl.textContent?.trim() : null;
    },
    title,
  );
};

const clickButton = async (page, label) => {
  await page.$$eval(
    'button',
    (buttons, targetLabel) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes(targetLabel),
      );
      if (target) target.click();
    },
    label,
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

  await page.goto(targetUrl, { waitUntil: 'networkidle0' });
  await page.waitForSelector('h1');

  if (source === 'chesscom') {
    await clickButton(page, 'Chess.com');
  }

  await page.waitForSelector('table');

  const positionsBefore = await getMetricValue(page, 'Positions');
  const tacticsBefore = await getMetricValue(page, 'Tactics');

  await clickButton(page, 'Backfill history');
  await new Promise((resolve) => setTimeout(resolve, 3000));
  await page.waitForSelector('table');

  const positionsAfterFirst = await getMetricValue(page, 'Positions');
  const tacticsAfterFirst = await getMetricValue(page, 'Tactics');

  await clickButton(page, 'Backfill history');
  await new Promise((resolve) => setTimeout(resolve, 3000));
  await page.waitForSelector('table');

  const positionsAfterSecond = await getMetricValue(page, 'Positions');
  const tacticsAfterSecond = await getMetricValue(page, 'Tactics');

  const outDir = path.resolve(__dirname);
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, screenshotName);
  await page.screenshot({ path: outPath, fullPage: true });

  await browser.close();

  if (
    positionsBefore !== positionsAfterFirst ||
    tacticsBefore !== tacticsAfterFirst ||
    positionsAfterFirst !== positionsAfterSecond ||
    tacticsAfterFirst !== tacticsAfterSecond
  ) {
    throw new Error(
      `Backfill changed counts: positions ${positionsBefore} -> ${positionsAfterFirst} -> ${positionsAfterSecond}, ` +
        `tactics ${tacticsBefore} -> ${tacticsAfterFirst} -> ${tacticsAfterSecond}`,
    );
  }

  if (consoleErrors.length) {
    console.error('Console errors detected:', consoleErrors);
    process.exit(1);
  }
})();
