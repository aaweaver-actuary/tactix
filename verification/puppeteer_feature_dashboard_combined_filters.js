const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');

const ROOT_DIR = path.resolve(__dirname, '..');
const CLIENT_DIR = path.resolve(ROOT_DIR, 'client');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const BACKEND_RUNNING = process.env.TACTIX_BACKEND_RUNNING === '1';
const DASHBOARD_URL =
  process.env.TACTIX_DASHBOARD_URL || 'http://localhost:4173';
const SCREENSHOT_DATE = new Date().toISOString().slice(0, 10);

function startBackend() {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      BACKEND_CMD,
      ['-m', 'uvicorn', 'tactix.api:app', '--host', '0.0.0.0', '--port', '8000'],
      {
        cwd: ROOT_DIR,
        env: { ...process.env },
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
        proc.stdout.off('data', onData);
        proc.stderr.off('data', onData);
        resolve(proc);
      }
    };

    proc.stdout.on('data', onData);
    proc.stderr.on('data', onData);
    proc.on('error', reject);
  });
}

async function waitForDashboard(page) {
  await page.waitForSelector('[data-testid="filter-source"]:not([disabled])', {
    timeout: 60000,
  });
  await page.waitForSelector('table', { timeout: 60000 });
}

async function selectDashboardSource(page, value) {
  await page.waitForSelector('[data-testid="filter-source"]:not([disabled])', {
    timeout: 60000,
  });
  await page.select('[data-testid="filter-source"]', value);
}

async function selectTimeControl(page) {
  await page.waitForSelector(
    '[data-testid="filter-time-control"]:not([disabled])',
    { timeout: 60000 },
  );
  const options = await page.$$('[data-testid="filter-time-control"] option');
  for (const option of options) {
    const handle = await option.getProperty('value');
    const value = (await handle.jsonValue()) || '';
    if (value && value !== 'all') {
      await page.select('[data-testid="filter-time-control"]', value);
      return value;
    }
  }
  return null;
}

(async () => {
  console.log('Starting backend...');
  const backend = BACKEND_RUNNING ? null : await startBackend();
  console.log('Starting preview server...');
  const preview = await startPreview();
  try {
    console.log('Launching browser...');
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    page.setDefaultTimeout(60000);
    const consoleErrors = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (err) => consoleErrors.push(err.toString()));
    page.on('requestfailed', (request) => {
      const errorText = request.failure()?.errorText || 'unknown';
      if (!errorText.includes('ERR_ABORTED')) {
        consoleErrors.push(`Request failed: ${request.url()} (${errorText})`);
      }
    });

    console.log('Navigating to dashboard...');
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle0', timeout: 60000 });
    await waitForDashboard(page);

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });

    const combinedPath = path.join(
      outDir,
      `feature-dashboard-combined-${SCREENSHOT_DATE}.png`,
    );
    await page.screenshot({ path: combinedPath, fullPage: true });
    console.log('Saved screenshot to', combinedPath);

    await selectDashboardSource(page, 'chesscom');
    await waitForDashboard(page);

    const chesscomPath = path.join(
      outDir,
      `feature-dashboard-chesscom-${SCREENSHOT_DATE}.png`,
    );
    await page.screenshot({ path: chesscomPath, fullPage: true });
    console.log('Saved screenshot to', chesscomPath);

    const timeControl = await selectTimeControl(page);
    await waitForDashboard(page);

    const timeControlPath = path.join(
      outDir,
      `feature-dashboard-time-control-${timeControl || 'selected'}-${SCREENSHOT_DATE}.png`,
    );
    await page.screenshot({ path: timeControlPath, fullPage: true });
    console.log('Saved screenshot to', timeControlPath);

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      throw new Error('Console errors detected during UI verification');
    }

    await browser.close();
  } finally {
    preview.kill();
    if (backend) backend.kill();
  }
})();
