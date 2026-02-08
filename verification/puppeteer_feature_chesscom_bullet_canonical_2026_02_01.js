const fs = require('fs');
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
const BACKEND_PORT = process.env.TACTIX_BACKEND_PORT || '8002';
const DEV_SERVER_PORT = process.env.TACTIX_UI_PORT || '5179';
const API_BASE =
  process.env.TACTIX_API_BASE || `http://localhost:${BACKEND_PORT}`;
const TARGET_URL =
  process.env.TACTIX_UI_URL || `http://localhost:${DEV_SERVER_PORT}/`;
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-chesscom-bullet-canonical-2026-02-01.png';
const API_TOKEN = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const TEST_USER = process.env.TACTIX_TEST_CHESSCOM_USER || 'groborger';
const LOG_PATH =
  process.env.TACTIX_LOG_PATH ||
  path.resolve(
    ROOT_DIR,
    'tmp-logs',
    'feature_chesscom_bullet_canonical_ui_2026_02_07.json',
  );
const DB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.resolve(
    ROOT_DIR,
    'tmp-logs',
    'feature_chesscom_bullet_canonical_ui_2026_02_07.duckdb',
  );

function startBackend() {
  return new Promise((resolve, reject) => {
    fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
    if (fs.existsSync(DB_PATH)) {
      fs.unlinkSync(DB_PATH);
    }
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
          TACTIX_API_TOKEN: API_TOKEN,
          TACTIX_DUCKDB_PATH: DB_PATH,
          TACTIX_SOURCE: 'chesscom',
          TACTIX_USER: TEST_USER,
          TACTIX_CHESSCOM_PROFILE: 'bullet',
          TACTIX_CHESSCOM_USE_FIXTURE: '1',
          TACTIX_USE_FIXTURE: '1',
          CHESSCOM_USERNAME: TEST_USER,
          CHESSCOM_USER: TEST_USER,
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

async function runPipeline() {
  const url = new URL(`${API_BASE}/api/pipeline/run`);
  url.searchParams.set('source', 'chesscom');
  url.searchParams.set('profile', 'bullet');
  url.searchParams.set('user_id', TEST_USER);
  url.searchParams.set('start_date', '2026-02-01');
  url.searchParams.set('end_date', '2026-02-01');
  url.searchParams.set('use_fixture', 'true');
  url.searchParams.set('fixture_name', 'chesscom_2_bullet_games.pgn');
  url.searchParams.set('reset_db', 'true');

  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Pipeline run failed: ${response.status} ${body}`);
  }
  return response.json();
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForHealth(retries = 20, delayMs = 500) {
  const url = new URL(`${API_BASE}/api/health`);
  for (let attempt = 0; attempt < retries; attempt += 1) {
    try {
      const response = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${API_TOKEN}` },
      });
      if (response.ok) {
        return;
      }
    } catch (err) {
      // ignore until retries exhausted
    }
    await sleep(delayMs);
  }
  throw new Error('Backend health check failed');
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
  let runError = null;

  try {
    if (!BACKEND_RUNNING) {
      console.log('Starting backend...');
      backend = await startBackend();
    }

    await waitForHealth();

    console.log('Running pipeline fixture...');
    const payload = await runPipeline();
    fs.mkdirSync(path.dirname(LOG_PATH), { recursive: true });
    fs.writeFileSync(LOG_PATH, JSON.stringify(payload, null, 2));

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
    console.error('UI verification failed:', err);
    runError = err;
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    if (devServer) devServer.kill();
    if (backend) backend.kill();
  }
  if (runError) {
    return;
  }
})();
