const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');

const ROOT_DIR = path.resolve(__dirname, '..');
const CLIENT_DIR = path.resolve(ROOT_DIR, 'client');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const BACKEND_RUNNING = process.env.TACTIX_BACKEND_RUNNING === '1';
const BACKEND_PORT = process.env.TACTIX_BACKEND_PORT || '8001';
const DEV_SERVER_PORT = process.env.TACTIX_UI_PORT || '5178';
const DUCKDB_PATH = process.env.TACTIX_DUCKDB_PATH;
const API_BASE =
  process.env.TACTIX_API_BASE || `http://localhost:${BACKEND_PORT}`;
const TARGET_URL =
  process.env.TACTIX_UI_URL || `http://localhost:${DEV_SERVER_PORT}/`;
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'issue-6-chesscom-bullet-canonical-2026-02-01.png';

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
        BACKEND_PORT,
      ],
      {
        cwd: ROOT_DIR,
        env: {
          ...process.env,
          ...(DUCKDB_PATH ? { TACTIX_DUCKDB_PATH: DUCKDB_PATH } : {}),
          TACTIX_SOURCE: 'chesscom',
          TACTIX_USER: 'groborger',
          TACTIX_CHESSCOM_PROFILE: 'bullet',
          TACTIX_CHESSCOM_USE_FIXTURE: '1',
          TACTIX_USE_FIXTURE: '1',
          CHESSCOM_USERNAME: 'groborger',
          CHESSCOM_USER: 'groborger',
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

function startDevServer() {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      'npm',
      [
        '--prefix',
        CLIENT_DIR,
        'run',
        'dev',
        '--',
        '--host',
        '--port',
        DEV_SERVER_PORT,
      ],
      {
        stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env, VITE_API_BASE: API_BASE },
      },
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

async function setDateInput(page, selector, value) {
  await page.click(selector, { clickCount: 3 });
  await page.type(selector, value);
  await page.keyboard.press('Tab');
}

async function expandCard(page, selector) {
  const headerSelector = `${selector} [role="button"]`;
  await page.waitForSelector(headerSelector, { timeout: 60000 });
  await page.$eval(headerSelector, (el) =>
    el.scrollIntoView({ block: 'center' }),
  );
  await page.click(headerSelector);
}

(async () => {
  let backend = null;
  let devServer = null;
  let browser = null;
  let page = null;
  let consoleErrors = [];

  try {
    if (!BACKEND_RUNNING) {
      console.log('Starting backend...');
      backend = await startBackend();
    }
    console.log('Starting dev server...');
    devServer = await startDevServer();

    console.log('Launching browser...');
    browser = await puppeteer.launch({ headless: 'new' });
    page = await browser.newPage();
    consoleErrors = attachConsoleCapture(page);

    await page.goto(TARGET_URL, { waitUntil: 'networkidle0', timeout: 60000 });
    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: 60000,
    });

    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]');
    await page.select('[data-testid="filter-chesscom-profile"]', 'bullet');
    await page.waitForSelector('[data-testid="filter-time-control"]');
    await page.select('[data-testid="filter-time-control"]', 'bullet');
    await setDateInput(page, '[data-testid="filter-start-date"]', '2026-02-01');
    await setDateInput(page, '[data-testid="filter-end-date"]', '2026-02-01');

    await page.waitForSelector('[data-testid="recent-games-card"]');
    await page.waitForSelector('[data-testid="practice-queue-card"]');

    await expandCard(page, '[data-testid="recent-games-card"]');
    await expandCard(page, '[data-testid="practice-queue-card"]');

    await page.waitForFunction(
      () =>
        document.querySelectorAll('[data-testid^="recent-games-row-"]')
          .length === 2 &&
        document.querySelectorAll('[data-testid^="practice-queue-row-"]')
          .length === 2,
      { timeout: 120000 },
    );

    const recentRows = await page.$$('[data-testid^="recent-games-row-"]');
    const practiceRows = await page.$$('[data-testid^="practice-queue-row-"]');

    if (recentRows.length !== 2) {
      throw new Error(
        `Expected 2 recent games rows, found ${recentRows.length}`,
      );
    }
    if (practiceRows.length !== 2) {
      throw new Error(
        `Expected 2 practice queue rows, found ${practiceRows.length}`,
      );
    }

    const recentText = await page.$eval(
      '[data-testid="recent-games-card"]',
      (el) => el.textContent || '',
    );
    const winCount = recentText.split('Win').length - 1;
    const lossCount = recentText.split('Loss').length - 1;
    if (winCount < 1 || lossCount < 1) {
      throw new Error('Expected one win and one loss in recent games');
    }

    const outPath = await captureScreenshot(
      page,
      path.resolve(__dirname),
      SCREENSHOT_NAME,
    );
    console.log('Saved screenshot to', outPath);

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }
  } catch (err) {
    try {
      if (page) {
        const outPath = await captureScreenshot(
          page,
          path.resolve(__dirname),
          `failed-${SCREENSHOT_NAME}`,
        );
        console.error('Saved failure screenshot to', outPath);
      }
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Issue 6 UI verification failed:', err);
    process.exit(1);
  } finally {
    if (browser) await browser.close();
    if (devServer) devServer.kill();
    if (backend) backend.kill();
  }
})();
