const fs = require('fs');
const net = require('net');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const PGADMIN_URL = process.env.TACTIX_PGADMIN_URL || 'http://localhost:5050';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-129-pgadmin-login-2026-01-28.png';
const PGADMIN_EMAIL = process.env.TACTIX_PGADMIN_EMAIL || 'admin@tactix.io';
const PGADMIN_PASSWORD = process.env.TACTIX_PGADMIN_PASSWORD || 'tactix';

function isPortOpen(host, port, timeoutMs = 1000) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    let settled = false;

    const finalize = (result) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      resolve(result);
    };

    socket.setTimeout(timeoutMs);
    socket.once('connect', () => finalize(true));
    socket.once('timeout', () => finalize(false));
    socket.once('error', () => finalize(false));
    socket.connect(port, host);
  });
}

(async () => {
  const portOpen = await isPortOpen('127.0.0.1', 5050);
  if (!portOpen) {
    throw new Error('PgAdmin is not reachable on http://localhost:5050');
  }

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

  await page.goto(PGADMIN_URL, { waitUntil: 'networkidle0' });
  await page.waitForFunction(
    () =>
      document.querySelector('input[name="email"]') &&
      document.querySelector('input[name="password"]'),
    { timeout: 45000 },
  );

  await page.type('input[name="email"]', PGADMIN_EMAIL, { delay: 20 });
  await page.type('input[name="password"]', PGADMIN_PASSWORD, {
    delay: 20,
  });
  await page.click('button[type="submit"]');

  await page.waitForFunction(
    () => document.body && document.body.innerText.includes('Dashboard'),
    { timeout: 15000 },
  );

  const outDir = path.resolve(__dirname);
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, SCREENSHOT_NAME);
  await page.screenshot({ path: outPath, fullPage: true });

  await browser.close();

  if (consoleErrors.length) {
    console.error('Console errors detected:', consoleErrors);
    process.exit(1);
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
