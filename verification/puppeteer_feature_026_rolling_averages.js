const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const net = require('net');
const puppeteer = require('puppeteer');

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const CLIENT_DIR = path.join(ROOT_DIR, 'client');
const DASHBOARD_URL =
  process.env.TACTIX_DASHBOARD_URL || 'http://localhost:5173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-026-rolling-averages-2026-01-25.png';
const RUN_BUTTON_SELECTOR =
  process.env.TACTIX_RUN_SELECTOR || 'button.button.bg-teal.font-display';
const FRONTEND_HOST = '127.0.0.1';
const FRONTEND_PORT = 5173;

function waitForPort(host, port, timeoutMs = 30000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const socket = net.connect(port, host);
      socket.on('connect', () => {
        socket.destroy();
        resolve(true);
      });
      socket.on('error', () => {
        socket.destroy();
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`Timed out waiting for ${host}:${port}`));
          return;
        }
        setTimeout(attempt, 250);
      });
    };
    attempt();
  });
}

async function startFrontendIfNeeded() {
  try {
    await waitForPort(FRONTEND_HOST, FRONTEND_PORT, 1000);
    return null;
  } catch (err) {
    const proc = spawn(
      'npm',
      [
        '--prefix',
        CLIENT_DIR,
        'run',
        'dev',
        '--',
        '--host',
        '0.0.0.0',
        '--port',
        String(FRONTEND_PORT),
        '--strictPort',
      ],
      {
        cwd: ROOT_DIR,
        env: { ...process.env },
        stdio: 'ignore',
        detached: true,
      },
    );
    proc.unref();
    await waitForPort(FRONTEND_HOST, FRONTEND_PORT, 30000);
    return proc;
  }
}

async function isBackendRunning() {
  try {
    await waitForPort('127.0.0.1', 8000, 1000);
    return true;
  } catch (err) {
    return false;
  }
}

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

(async () => {
  await startFrontendIfNeeded();
  const backendRunning = await isBackendRunning();
  console.log('Starting backend...');
  const backend = backendRunning ? null : await startBackend();
  try {
    console.log('Launching browser...');
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    const consoleErrors = [];
    page.setDefaultNavigationTimeout(60000);

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    page.on('pageerror', (err) => {
      consoleErrors.push(err.toString());
    });
    page.on('requestfailed', (request) => {
      consoleErrors.push(
        `Request failed: ${request.url()} (${request.failure()?.errorText || 'unknown'})`,
      );
    });

    console.log('Navigating to dashboard...');
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('[data-testid="filter-source"]');
    await page.waitForSelector(RUN_BUTTON_SELECTOR);
    await page.click(RUN_BUTTON_SELECTOR);

    await page.waitForSelector('table');
    await page.waitForSelector('span.px-2.py-1.text-xs.rounded-full');
    await page.waitForSelector('table thead th:nth-child(2)');
    await page.waitForSelector('table thead th:nth-child(3)');

    const outDir = path.resolve(__dirname);
    const outPath = path.join(outDir, SCREENSHOT_NAME);
    fs.mkdirSync(outDir, { recursive: true });
    await page.screenshot({ path: outPath, fullPage: true });
    console.log('Saved screenshot to', outPath);

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      throw new Error('Console errors detected during UI verification');
    }

    await browser.close();
  } finally {
    if (backend) {
      backend.kill();
    }
  }
})();
