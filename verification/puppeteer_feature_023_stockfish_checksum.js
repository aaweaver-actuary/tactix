const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const puppeteer = require('puppeteer');

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const DASHBOARD_URL = process.env.TACTIX_DASHBOARD_URL || 'http://localhost:5173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-023-stockfish-checksum-2026-01-25.png';
const RUN_BUTTON_SELECTOR =
  process.env.TACTIX_RUN_SELECTOR || 'button.button.bg-teal.font-display';

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
  console.log('Starting backend...');
  const backend = await startBackend();
  try {
    console.log('Launching browser...');
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    const consoleErrors = [];
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
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle0' });
    await page.waitForSelector('[data-testid="filter-source"]');
    await page.waitForSelector(RUN_BUTTON_SELECTOR);
    await page.click(RUN_BUTTON_SELECTOR);
    await page.waitForSelector('table');

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
    backend.kill();
  }
})();