const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const apiBase = process.env.TACTIX_API_BASE || 'http://localhost:8000';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-107-fen-positions-ci-2026-01-27.png';
const source = process.env.TACTIX_SOURCE || 'lichess';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

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

    const result = await page.evaluate(
      async (base, token, sourceValue) => {
        const response = await fetch(`${base}/api/dashboard?source=${sourceValue}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          throw new Error(`Dashboard fetch failed: ${response.status}`);
        }
        const data = await response.json();
        const positions = Array.isArray(data.positions) ? data.positions : [];
        const hasFen = positions.some(
          (pos) => typeof pos.fen === 'string' && pos.fen.length > 10,
        );
        return { count: positions.length, hasFen };
      },
      apiBase,
      apiToken,
      source,
    );

    if (!result.count || !result.hasFen) {
      throw new Error('Expected dashboard positions with FEN data');
    }

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });

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
    console.error('Feature 107 CI verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();