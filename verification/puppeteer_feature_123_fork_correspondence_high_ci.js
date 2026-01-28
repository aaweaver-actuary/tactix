const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');

const ROOT_DIR = path.resolve(__dirname, '..');
console.log('Starting feature 123 Puppeteer run...');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const DUCKDB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.join(ROOT_DIR, 'data', 'tactix.duckdb');
const API_BASE = process.env.TACTIX_API_BASE || 'http://localhost:8000';
const DASHBOARD_URL = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-123-fork-correspondence-high-severity-ci-2026-01-28.png';

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
          TACTIX_CHESSCOM_PROFILE: 'correspondence',
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

async function ensureBackend() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1500);
    const res = await fetch('http://localhost:8000/api/health', {
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (res.ok) {
      return null;
    }
  } catch (err) {
    // Fall back to starting a local backend.
  }
  return startBackend();
}

(async () => {
  const backend = await ensureBackend();
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
    await page.select(
      '[data-testid="filter-chesscom-profile"]',
      'correspondence',
    );
    await page.select('[data-testid="filter-motif"]', 'fork');
    await page.select('[data-testid="filter-time-control"]', '86400');

    await page.click('[data-testid="action-run"]');
    await page.waitForSelector('table');
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const rows = await page.$$eval('table tbody tr', (items) =>
      items.map((row) => row.textContent || ''),
    );
    const hasForkRow = rows.some((row) => row.toLowerCase().includes('fork'));
    if (!hasForkRow) {
      throw new Error('Expected a fork row in tactics table');
    }

    const severityCheck = await page.evaluate(async (apiBase) => {
      const res = await fetch(
        `${apiBase}/api/dashboard?source=chesscom&motif=fork&time_control=86400`,
        {
          headers: { Authorization: 'Bearer local-dev-token' },
        },
      );
      if (!res.ok) {
        throw new Error(`Dashboard fetch failed: ${res.status}`);
      }
      return res.json();
    }, API_BASE);

    const hasHighSeverity = Array.isArray(severityCheck?.tactics)
      ? severityCheck.tactics.some(
          (row) => row.best_uci === 'f4e2' && row.severity >= 1.5,
        )
      : false;

    if (!hasHighSeverity) {
      throw new Error('Expected fork tactic with high severity (>= 1.5)');
    }

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, SCREENSHOT_NAME);
    await page.screenshot({ path: outPath, fullPage: true });
    console.log(`Saved screenshot: ${outPath}`);

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
