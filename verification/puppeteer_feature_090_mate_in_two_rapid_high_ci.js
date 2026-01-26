const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');

const ROOT_DIR = path.resolve(__dirname, '..');
const CLIENT_DIR = path.resolve(ROOT_DIR, 'client');
console.log('Starting feature 090 Puppeteer CI run...');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const DUCKDB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.join(ROOT_DIR, 'client', 'data', 'tactix.duckdb');
const API_BASE = process.env.TACTIX_API_BASE || 'http://localhost:8000';
const DASHBOARD_URL = process.env.TACTIX_UI_URL || 'http://localhost:4173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-090-mate-in-2-rapid-high-severity-ci-2026-01-26.png';

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

function startPreview() {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      'npm',
      ['--prefix', CLIENT_DIR, 'run', 'preview', '--', '--host', '--port', '4173'],
      { stdio: ['ignore', 'pipe', 'pipe'] },
    );

    const onData = (data) => {
      const text = data.toString();
      if (text.includes('Local:')) {
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
  const preview = await startPreview();
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

    await page.setDefaultNavigationTimeout(60000);
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-testid="filter-source"]');

    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]');
    await page.select('[data-testid="filter-chesscom-profile"]', 'rapid');
    await page.select('[data-testid="filter-motif"]', 'mate');
    await page.select('[data-testid="filter-time-control"]', '600');

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

    const severityCheck = await page.evaluate(async (apiBase) => {
      const res = await fetch(
        `${apiBase}/api/dashboard?source=chesscom&motif=mate&time_control=600`,
        {
          headers: { Authorization: 'Bearer local-dev-token' },
        },
      );
      if (!res.ok) {
        throw new Error(`Dashboard fetch failed: ${res.status}`);
      }
      return res.json();
    }, API_BASE);

    const mateRow = Array.isArray(severityCheck?.tactics)
      ? severityCheck.tactics.find((row) => row.best_uci === 'c5f2')
      : null;

    if (!mateRow || mateRow.severity < 1.5) {
      throw new Error('Expected mate-in-two tactic with high severity (>= 1.5)');
    }

    if (!mateRow.best_san || !String(mateRow.explanation || '').includes('Best line')) {
      throw new Error('Expected best line and explanation for mate-in-two tactic');
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
    if (preview) {
      preview.kill();
    }
    if (backend) {
      backend.kill();
    }
  }
})();
