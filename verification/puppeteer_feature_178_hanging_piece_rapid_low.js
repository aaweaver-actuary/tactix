const fs = require('fs');
const net = require('net');
const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const DUCKDB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.join(ROOT_DIR, 'data', 'tactix.duckdb');
const DASHBOARD_URL = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-178-hanging-piece-rapid-low-severity-2026-01-29.png';

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

function startBackend() {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      BACKEND_CMD,
      [
        '-m',
        'uvicorn',
        'tactix.api:app',
        '--host',
        '0.0.0.0',
        '--port',
        '8000',
      ],
      {
        cwd: ROOT_DIR,
        env: {
          ...process.env,
          TACTIX_DUCKDB_PATH: DUCKDB_PATH,
          TACTIX_SOURCE: 'chesscom',
          TACTIX_USER: 'chesscom',
          TACTIX_CHESSCOM_PROFILE: 'rapid',
          TACTIX_CHESSCOM_USE_FIXTURE: '1',
          TACTIX_USE_FIXTURE: '1',
          CHESSCOM_USERNAME: 'chesscom',
          CHESSCOM_USER: 'chesscom',
        },
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
  const backendRunning = await isPortOpen('127.0.0.1', 8000);
  const backend = backendRunning ? null : await startBackend();
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
    await page.select('[data-testid="filter-chesscom-profile"]', 'rapid');
    await page.select('[data-testid="filter-motif"]', 'hanging_piece');

    await page.click('[data-testid="action-run"]');
    await page.waitForSelector('table');
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const rows = await page.$$('table tbody tr');
    const rowTexts = [];
    for (const row of rows) {
      // eslint-disable-next-line no-await-in-loop
      const text = await row.evaluate((el) => el.textContent || '');
      rowTexts.push(text);
    }
    const hasHangingPiece = rowTexts.some((row) =>
      row.toLowerCase().includes('hanging_piece'),
    );
    if (!hasHangingPiece) {
      throw new Error('Expected a hanging piece row in tactics table');
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
    if (backend) {
      backend.kill();
    }
  }
})();
