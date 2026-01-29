const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');

const ROOT_DIR = path.resolve(__dirname, '..');
console.log('Starting feature 173 Puppeteer run...');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const DUCKDB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.join(ROOT_DIR, 'data', 'tactix_feature_173.duckdb');
const CHECKPOINT_PATH =
  process.env.TACTIX_CHESSCOM_CHECKPOINT_PATH ||
  path.join(ROOT_DIR, 'data', 'chesscom_feature_173_cursor.txt');
const ANALYSIS_CHECKPOINT_PATH =
  process.env.TACTIX_ANALYSIS_CHECKPOINT_PATH ||
  path.join(ROOT_DIR, 'data', 'analysis_checkpoint_feature_173.json');
const API_BASE = process.env.TACTIX_API_BASE || 'http://localhost:8000';
const DASHBOARD_URL = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const CHESSCOM_PROFILE = process.env.TACTIX_CHESSCOM_PROFILE || 'correspondence';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-173-discovered-check-correspondence-high-severity-ci-2026-01-29.png';
const EXPECTED_GAME_ID =
  process.env.TACTIX_DISCOVERED_CHECK_GAME_ID ||
  'correspondence-discovered-check-high';
const MIN_SEVERITY = process.env.TACTIX_DISCOVERED_CHECK_MIN_SEVERITY
  ? Number(process.env.TACTIX_DISCOVERED_CHECK_MIN_SEVERITY)
  : 1.5;

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
          TACTIX_CHESSCOM_CHECKPOINT_PATH: CHECKPOINT_PATH,
          TACTIX_ANALYSIS_CHECKPOINT_PATH: ANALYSIS_CHECKPOINT_PATH,
          TACTIX_SOURCE: 'chesscom',
          TACTIX_USER: 'chesscom',
          TACTIX_CHESSCOM_PROFILE: CHESSCOM_PROFILE,
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
    await page.waitForFunction(() => {
      const select = document.querySelector('[data-testid="filter-source"]');
      const button = document.querySelector('[data-testid="action-run"]');
      return (
        select instanceof HTMLSelectElement &&
        select.value === 'chesscom' &&
        button &&
        !button.hasAttribute('disabled')
      );
    });
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]');
    await page.select('[data-testid="filter-chesscom-profile"]', CHESSCOM_PROFILE);
    await page.waitForFunction(
      (profileValue) => {
        const profile = document.querySelector(
          '[data-testid="filter-chesscom-profile"]',
        );
        return (
          profile instanceof HTMLSelectElement && profile.value === profileValue
        );
      },
      {},
      CHESSCOM_PROFILE,
    );

    await page.waitForFunction(() => {
      const button = document.querySelector('[data-testid="action-run"]');
      return button && !button.hasAttribute('disabled');
    });

    await page.click('[data-testid="action-run"]');
    await page.waitForFunction(
      () => {
        const button = document.querySelector('[data-testid="action-run"]');
        if (!button) return false;
        const label = button.textContent || '';
        return !button.hasAttribute('disabled') && !label.includes('Running');
      },
      { timeout: 60000 },
    );

    await page.select('[data-testid="filter-motif"]', 'discovered_check');
    await page.waitForFunction(() => {
      const motif = document.querySelector('[data-testid="filter-motif"]');
      return motif instanceof HTMLSelectElement && motif.value === 'discovered_check';
    });

    await page.waitForFunction(() => {
      const button = document.querySelector('[data-testid="action-run"]');
      return button && !button.hasAttribute('disabled');
    });

    await page.click('[data-testid="dashboard-card-tactics-table"] [role="button"]');
    await page.waitForFunction(() => {
      const header = document.querySelector(
        '[data-testid="dashboard-card-tactics-table"] [role="button"]',
      );
      return header?.getAttribute('aria-expanded') === 'true';
    });
    await page.waitForSelector(
      '[data-testid="dashboard-card-tactics-table"] table',
    );
    await new Promise((resolve) => setTimeout(resolve, 3000));

    const rows = await page.$$eval(
      '[data-testid="dashboard-card-tactics-table"] table tbody tr',
      (items) => items.map((row) => row.textContent || ''),
    );
    const hasDiscoveredCheck = rows.some((row) =>
      row.toLowerCase().includes('discovered_check'),
    );
    if (!hasDiscoveredCheck) {
      throw new Error('Expected a discovered check row in tactics table');
    }

    const severityCheck = await page.evaluate(
      async (apiBase, expectedGameId, minSeverity) => {
        const res = await fetch(
          `${apiBase}/api/dashboard?source=chesscom&motif=discovered_check&time_control=86400`,
          {
            headers: { Authorization: 'Bearer local-dev-token' },
          },
        );
        if (!res.ok) {
          throw new Error(`Dashboard fetch failed: ${res.status}`);
        }
        const data = await res.json();
        return Array.isArray(data?.tactics)
          ? data.tactics.some((row) => {
              if (row.motif !== 'discovered_check') return false;
              if (expectedGameId && row.game_id !== expectedGameId) return false;
              return Number(row.severity) >= minSeverity;
            })
          : false;
      },
      API_BASE,
      EXPECTED_GAME_ID,
      MIN_SEVERITY,
    );

    if (!severityCheck) {
      throw new Error('Expected discovered check tactic with high severity (>= 1.5)');
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
