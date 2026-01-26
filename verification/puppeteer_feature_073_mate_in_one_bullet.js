const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const DUCKDB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.join(ROOT_DIR, 'client', 'data', 'tactix.duckdb');
const DASHBOARD_URL = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-073-mate-in-1-low-severity-2026-01-26.png';

function startBackend() {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      BACKEND_CMD,
      ['-m', 'uvicorn', 'tactix.api:app', '--host', '0.0.0.0', '--port', '8000'],
      {
        cwd: ROOT_DIR,
        env: { ...process.env, TACTIX_DUCKDB_PATH: DUCKDB_PATH },
        stdio: ['ignore', 'pipe', 'pipe'],
      },
    );

    const onData = (data) => {
      const text = data.toString();
      if (text.includes('Uvicorn running')) {
        cleanup();
        resolve(proc);
      }
    };

    const onError = (err) => {
      cleanup();
      reject(err);
    };

    function cleanup() {
      proc.stdout.off('data', onData);
      proc.stderr.off('data', onData);
      proc.off('error', onError);
    }

    proc.stdout.on('data', onData);
    proc.stderr.on('data', onData);
    proc.on('error', onError);
  });
}

(async () => {
  const backend = await startBackend();
  try {
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

    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle0' });
    await page.waitForSelector('[data-testid="filter-source"]');

    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]');
    await page.select('[data-testid="filter-chesscom-profile"]', 'bullet');
    await page.select('[data-testid="filter-motif"]', 'mate');
    await page.select('[data-testid="filter-time-control"]', '60');

    await page.click('[data-testid="action-run"]');
    await page.waitForSelector('table');
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const rows = await page.$$eval('table tbody tr', (items) =>
      items.map((row) => row.textContent || ''),
    );
    const hasMateRow = rows.some((row) => row.toLowerCase().includes('mate'));
    if (!hasMateRow) {
      throw new Error('Expected a mate row in tactics table');
    }

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, SCREENSHOT_NAME);
    await page.screenshot({ path: outPath, fullPage: true });

    await browser.close();

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
  } finally {
    backend.kill();
  }
})();
