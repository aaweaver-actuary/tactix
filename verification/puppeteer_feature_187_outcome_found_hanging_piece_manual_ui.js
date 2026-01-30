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
  'feature-187-outcome-found-hanging-piece-manual-2026-01-29.png';

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

async function waitForDashboardPaint(delayMs = 2000) {
  await new Promise((resolve) => setTimeout(resolve, delayMs));
}

async function waitForDashboardResponse(page) {
  await page.waitForResponse(
    (response) =>
      response.url().includes('/api/dashboard') && response.status() === 200,
    { timeout: 30000 },
  );
}

async function expandCard(page, title) {
  const headings = await page.$$('h3');
  const normalized = title.trim().toLowerCase();
  for (const heading of headings) {
    const text = await heading.evaluate((el) =>
      (el.textContent || '').trim().toLowerCase(),
    );
    if (text !== normalized) continue;
    const buttonHandle = await heading.evaluateHandle((el) =>
      el.closest('[role="button"]'),
    );
    const button = buttonHandle.asElement();
    if (!button) return;
    const expanded = await button.evaluate((el) =>
      el.getAttribute('aria-expanded'),
    );
    if (expanded === 'false') {
      await button.click();
    }
    return;
  }
}

async function getRecentTacticsTable(page) {
  const headings = await page.$$('h3');
  for (const heading of headings) {
    const text = await heading.evaluate((el) =>
      (el.textContent || '').trim().toLowerCase(),
    );
    if (text !== 'recent tactics') continue;
    const tableHandle = await heading.evaluateHandle((el) =>
      el.closest('.card')?.querySelector('table'),
    );
    const table = tableHandle.asElement();
    if (table) return table;
  }
  throw new Error('Recent tactics table not found');
}

async function tableHasResult(table, resultText) {
  const rows = await table.$$('tbody tr');
  const expected = resultText.toLowerCase();
  for (const row of rows) {
    const text = await row.evaluate((el) =>
      (el.textContent || '').toLowerCase(),
    );
    if (text.includes(expected)) {
      return true;
    }
  }
  return false;
}

(async () => {
  const backendRunning = await isPortOpen('127.0.0.1', 8000);
  const backend = backendRunning ? null : await startBackend();
  try {
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    const consoleErrors = [];
    const ignoredConsolePatterns = [
      /Encountered two children with the same key/i,
    ];

    page.on('console', (msg) => {
      const text = msg.text();
      if (msg.type() !== 'error') return;
      if (ignoredConsolePatterns.some((pattern) => pattern.test(text))) {
        return;
      }
      consoleErrors.push(text);
    });
    page.on('pageerror', (err) => consoleErrors.push(err.toString()));
    page.on('requestfailed', (request) => {
      consoleErrors.push(
        `Request failed: ${request.url()} (${request.failure()?.errorText || 'unknown'})`,
      );
    });

    await page.goto(DASHBOARD_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: 60000,
    });

    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]', {
      timeout: 60000,
    });

    await page.waitForSelector('table', { timeout: 60000 });
    await waitForDashboardPaint(2000);

    await expandCard(page, 'Recent tactics');
    await waitForDashboardPaint(500);

    await Promise.all([
      waitForDashboardResponse(page),
      page.select('[data-testid="filter-time-control"]', 'all'),
    ]);
    await Promise.all([
      waitForDashboardResponse(page),
      page.select('[data-testid="filter-rating"]', 'all'),
    ]);

    await page.select('[data-testid="filter-chesscom-profile"]', 'rapid');
    await Promise.all([
      waitForDashboardResponse(page),
      page.select('[data-testid="filter-motif"]', 'hanging_piece'),
    ]);

    await waitForDashboardPaint(1200);
    const table = await getRecentTacticsTable(page);
    const hasFound = await tableHasResult(table, 'found');
    if (!hasFound) {
      throw new Error('Expected found outcome rows for hanging piece (rapid)');
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
