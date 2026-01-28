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
const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-146-base-card-ci-2026-01-28.png';
const DASHBOARD_PARSED = new URL(targetUrl);
const UI_HOST = DASHBOARD_PARSED.hostname || '127.0.0.1';
const UI_PORT = Number(DASHBOARD_PARSED.port || '5173');

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

async function waitForPort(host, port, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    // eslint-disable-next-line no-await-in-loop
    const open = await isPortOpen(host, port, 1000);
    if (open) return true;
    // eslint-disable-next-line no-await-in-loop
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  return false;
}

async function startFrontend(port) {
  const proc = spawn(
    'npm',
    ['--prefix', 'client', 'run', 'dev', '--', '--host', '0.0.0.0', '--port', String(port)],
    {
      cwd: ROOT_DIR,
      env: {
        ...process.env,
        BROWSER: 'none',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );

  const ready = await waitForPort(UI_HOST, port);
  if (!ready) {
    proc.kill();
    throw new Error('Frontend did not start in time');
  }
  return proc;
}

function startBackend() {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      BACKEND_CMD,
      ['-m', 'uvicorn', 'tactix.api:app', '--host', '0.0.0.0', '--port', '8000'],
      {
        cwd: ROOT_DIR,
        env: {
          ...process.env,
          TACTIX_DUCKDB_PATH: DUCKDB_PATH,
          TACTIX_SOURCE: 'lichess',
          TACTIX_USER: 'lichess',
          TACTIX_USE_FIXTURE: '1',
          TACTIX_LICHESS_PROFILE: 'rapid',
          LICHESS_USERNAME: 'lichess',
          LICHESS_USER: 'lichess',
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
  const frontendRunning = await isPortOpen(UI_HOST, UI_PORT);
  const frontend = frontendRunning ? null : await startFrontend(UI_PORT);
  let browser;
  let page;
  const consoleErrors = [];

  try {
    browser = await puppeteer.launch({ headless: 'new' });
    page = await browser.newPage();

    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (err) => consoleErrors.push(err.toString()));
    page.on('requestfailed', (request) => {
      consoleErrors.push(
        `Request failed: ${request.url()} (${request.failure()?.errorText || 'unknown'})`,
      );
    });

    await page.goto(targetUrl, { waitUntil: 'networkidle0', timeout: 60000 });
    await page.waitForSelector(
      '[data-testid="motif-breakdown"] > [role="button"]',
      {
        timeout: 60000,
      },
    );

    const headerSelector = '[data-testid="motif-breakdown"] > [role="button"]';
    const expandedSelector =
      '[data-testid="motif-breakdown"] > [data-state="expanded"]';
    const collapsedSelector =
      '[data-testid="motif-breakdown"] > [data-state="collapsed"]';

    const initialExpanded = await page.$eval(headerSelector, (el) =>
      el.getAttribute('aria-expanded'),
    );
    if (initialExpanded !== 'false') {
      throw new Error('Expected card to start collapsed');
    }

    await page.click(headerSelector);
    await page.waitForSelector(expandedSelector, { timeout: 60000 });

    const expandedValue = await page.$eval(headerSelector, (el) =>
      el.getAttribute('aria-expanded'),
    );
    if (expandedValue !== 'true') {
      throw new Error('Expected card to expand after click');
    }

    await page.click(headerSelector);
    await page.waitForSelector(collapsedSelector, { timeout: 60000 });

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
      if (page) {
        await page.screenshot({ path: outPath, fullPage: true });
      }
      console.error('Saved failure screenshot to', outPath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Feature 146 CI verification failed:', err);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
    if (backend) {
      backend.kill();
    }
    if (frontend) {
      frontend.kill();
    }
  }
})();
