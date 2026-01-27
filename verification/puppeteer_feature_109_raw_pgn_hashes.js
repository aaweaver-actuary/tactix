const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const baseUrl = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const today = new Date().toISOString().slice(0, 10);
const screenshotPrefix =
  process.env.TACTIX_SCREENSHOT_PREFIX ||
  `feature-109-raw-pgn-summary-${today}`;
const sources = ['lichess', 'chesscom'];

async function takeScreenshot(page, filename) {
  const outDir = path.resolve(__dirname);
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, filename);
  await page.screenshot({ path: outPath, fullPage: true });
  return outPath;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = [];

  await page.setExtraHTTPHeaders({ Authorization: `Bearer ${apiToken}` });

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(err.toString()));

  try {
    for (const source of sources) {
      const url = `${baseUrl}/api/raw_pgns/summary?source=${encodeURIComponent(source)}`;
      await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
      await delay(1000);
      const filename = `${screenshotPrefix}-${source}.png`;
      const savedPath = await takeScreenshot(page, filename);
      console.log(`Saved ${source} summary screenshot to ${savedPath}`);
    }

    const filteredErrors = consoleErrors.filter(
      (err) => !err.includes('status of 404') && !err.includes('favicon'),
    );
    if (filteredErrors.length) {
      console.error('Console errors detected:', filteredErrors);
      process.exit(1);
    }
  } catch (err) {
    console.error('Feature 109 raw PGN summary verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
