const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const { waitForHealth, runPipeline } = require('./helpers/backend_canonical_helpers');

const ROOT_DIR = path.resolve(__dirname, '..');
const CLIENT_DIR = path.resolve(ROOT_DIR, 'client');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const BACKEND_RUNNING = process.env.TACTIX_BACKEND_RUNNING === '1';
const BACKEND_PORT = process.env.TACTIX_BACKEND_PORT || '8004';
const DEV_SERVER_PORT = process.env.TACTIX_UI_PORT || '5181';
const API_BASE =
  process.env.TACTIX_API_BASE || `http://localhost:${BACKEND_PORT}`;
const API_TOKEN = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const TARGET_URL =
  process.env.TACTIX_UI_URL || `http://localhost:${DEV_SERVER_PORT}/`;
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-client-e2e-chesscom-bullet-2026-02-01.png';
const DUCKDB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.resolve(
    ROOT_DIR,
    'tmp-logs',
    'feature_client_e2e_chesscom_bullet_2026_02_01.duckdb',
  );
const RUN_DATE = '2026-02-01';
const TEST_USER = (
  process.env.TACTIX_TEST_CHESSCOM_USER || 'groborger'
).toLowerCase();

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
        '--strictPort',
      ],
      {
        stdio: ['ignore', 'pipe', 'pipe'],
        env: {
          ...process.env,
          VITE_API_BASE: API_BASE,
          VITE_PRACTICE_QUEUE_LIMIT:
            process.env.VITE_PRACTICE_QUEUE_LIMIT || '2',
        },
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

function launchBackend() {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      BACKEND_CMD,
      ['-m', 'uvicorn', 'tactix.api:app', '--host', '0.0.0.0', '--port', BACKEND_PORT],
      {
        cwd: ROOT_DIR,
        env: {
          ...process.env,
          TACTIX_API_TOKEN: API_TOKEN,
          TACTIX_SOURCE: 'chesscom',
          TACTIX_USER: TEST_USER,
          TACTIX_CHESSCOM_PROFILE: 'bullet',
          TACTIX_CHESSCOM_USE_FIXTURE: '1',
          TACTIX_USE_FIXTURE: '1',
          TACTIX_DUCKDB_PATH: DUCKDB_PATH,
          CHESSCOM_USERNAME: TEST_USER,
          CHESSCOM_USER: TEST_USER,
        },
        stdio: ['ignore', 'ignore', 'ignore'],
      },
    );

    proc.on('error', reject);
    resolve(proc);
  });
}

async function setDateInput(page, selector, value) {
  await page.click(selector, { clickCount: 3 });
  await page.type(selector, value);
  await page.keyboard.press('Tab');
}

async function ensureFiltersExpanded(page) {
  await page.waitForSelector('h3', { timeout: 60000 });
  await page.$$eval('h3', (headers) => {
    const target = headers.find(
      (header) => (header.textContent || '').trim() === 'Filters',
    );
    const button = target?.closest('[role="button"]');
    if (button && button.getAttribute('aria-expanded') === 'false') {
      button.click();
    }
  });
  await page.waitForFunction(
    () => {
      const input = document.querySelector('[data-testid="filter-source"]');
      return input && input.offsetParent !== null;
    },
    { timeout: 60000 },
  );
}

async function ensureCardExpanded(page, cardTestId) {
  const cardSelector = `[data-testid="${cardTestId}"]`;
  const headerSelector = `${cardSelector} [role="button"]`;
  await page.waitForSelector(headerSelector, { timeout: 60000 });
  const expanded = await page.$eval(headerSelector, (el) =>
    el.getAttribute('aria-expanded'),
  );
  if (expanded === 'false') {
    await page.click(headerSelector);
  }
  await page.waitForFunction(
    (selector) => {
      const node = document.querySelector(selector);
      return node && node.getAttribute('data-state') === 'expanded';
    },
    { timeout: 60000 },
    `${cardSelector} [data-state]`,
  );
}

async function applyFilters(page) {
  await ensureFiltersExpanded(page);

  await page.select('[data-testid="filter-source"]', 'chesscom');

  await page.waitForSelector('[data-testid="filter-chesscom-profile"]');
  await page.select('[data-testid="filter-chesscom-profile"]', 'bullet');
  await page.waitForSelector('[data-testid="filter-time-control"]');
  const timeControlValue = await page.$eval(
    '[data-testid="filter-time-control"]',
    (select) => {
      const options = Array.from(select.querySelectorAll('option')).map(
        (option) => option.value,
      );
      if (options.includes('bullet')) return 'bullet';
      if (options.includes('120+1')) return '120+1';
      return options.find((value) => value !== 'all') || 'all';
    },
  );
  await page.select('[data-testid="filter-time-control"]', timeControlValue);

  await setDateInput(page, '[data-testid="filter-start-date"]', RUN_DATE);
  await setDateInput(page, '[data-testid="filter-end-date"]', RUN_DATE);
}

async function step(label, fn) {
  try {
    return await fn();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`${label} failed: ${message}`);
  }
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
      fs.mkdirSync(path.dirname(DUCKDB_PATH), { recursive: true });
      if (fs.existsSync(DUCKDB_PATH)) {
        fs.unlinkSync(DUCKDB_PATH);
      }
      backend = await launchBackend();
    }

    console.log('Waiting for backend health...');
    await waitForHealth({ apiBase: API_BASE, apiToken: API_TOKEN });

    console.log('Running pipeline fixture...');
    await runPipeline({
      apiBase: API_BASE,
      apiToken: API_TOKEN,
      source: 'chesscom',
      profile: 'bullet',
      userId: TEST_USER,
      startDate: RUN_DATE,
      endDate: RUN_DATE,
      useFixture: true,
      fixtureName: 'chesscom_2_bullet_games.pgn',
      resetDb: true,
      retries: 3,
      retryDelayMs: 1000,
    });

    console.log('Starting dev server...');
    devServer = await startDevServer();

    console.log('Launching browser...');
    browser = await puppeteer.launch({ headless: 'new' });
    page = await browser.newPage();
    consoleErrors = attachConsoleCapture(page);

    console.log('Loading dashboard...');
    await step('Page navigation', async () => {
      await page.goto(TARGET_URL, { waitUntil: 'networkidle0', timeout: 60000 });
      await page.waitForSelector('[data-testid="filter-source"]', {
        timeout: 60000,
      });
    });

    console.log('Applying filters...');
    await step('Filter updates', async () => {
      await applyFilters(page);
    });

    console.log('Expanding cards...');
    await step('Expand recent games', async () => {
      await ensureCardExpanded(page, 'recent-games-card');
    });
    await step('Expand practice queue', async () => {
      await ensureCardExpanded(page, 'practice-queue-card');
    });

    console.log('Waiting for rows...');
    await step('Table readiness', async () => {
      await page.waitForFunction(
        () => {
          const recentRows = document.querySelectorAll(
            '[data-testid^="recent-games-row-"]',
          ).length;
          const practiceRows = document.querySelectorAll(
            '[data-testid^="practice-queue-row-"]',
          ).length;
          const recentText = document.querySelector(
            '[data-testid="recent-games-card"]',
          )?.textContent?.toLowerCase() || '';
          const practiceText = document.querySelector(
            '[data-testid="practice-queue-card"]',
          )?.textContent?.toLowerCase() || '';
          const recentReady =
            recentRows > 0 || recentText.includes('no rows');
          const practiceReady =
            practiceRows > 0 || practiceText.includes('no rows');
          return recentReady && practiceReady;
        },
        { timeout: 120000 },
      );
    });

    const recentRows = await page.$$('[data-testid^="recent-games-row-"]');
    const practiceRows = await page.$$('[data-testid^="practice-queue-row-"]');

    if (recentRows.length !== 2 || practiceRows.length !== 2) {
      throw new Error(
        `Expected 2 recent games rows and 2 practice rows, got ${recentRows.length} and ${practiceRows.length}.`,
      );
    }

    const resultLabels = await page.$$eval(
      '[data-testid^="recent-games-row-"]',
      (rows) =>
        rows.map((row) => {
          const cells = Array.from(row.querySelectorAll('td'));
          const resultCell = cells[2];
          return (resultCell?.textContent || '').trim().toLowerCase();
        }),
    );
    const winCount = resultLabels.filter((label) => label === 'win').length;
    const lossCount = resultLabels.filter((label) => label === 'loss').length;
    if (winCount !== 1 || lossCount !== 1) {
      throw new Error('Expected exactly one win and one loss in recent games');
    }

    const lossOpponent = await page.$$eval(
      '[data-testid^="recent-games-row-"]',
      (rows) => {
        for (const row of rows) {
          const cells = Array.from(row.querySelectorAll('td'));
          const resultCell = cells[2];
          const result = (resultCell?.textContent || '').trim().toLowerCase();
          if (result === 'loss') {
            return (cells[1]?.textContent || '').trim();
          }
        }
        return '';
      },
    );
    if (!lossOpponent) {
      throw new Error('Unable to determine loss opponent from recent games.');
    }

    const practiceLabels = await page.$$eval(
      '[data-testid^="practice-queue-row-"]',
      (rows) =>
        rows.map((row) => (row.textContent || '').toLowerCase()),
    );
    practiceLabels.forEach((text, index) => {
      if (!text.includes('missed')) {
        throw new Error(`Expected practice row ${index + 1} to be missed.`);
      }
    });

    for (const row of practiceRows) {
      await row.click();
      await page.waitForSelector('[data-testid="game-detail-modal"]', {
        visible: true,
      });
      await page.waitForSelector('[data-testid="game-detail-players"]');

      const playerText = await page.$eval(
        '[data-testid="game-detail-players"]',
        (node) => (node.textContent || '').toLowerCase(),
      );
      if (!playerText.includes(lossOpponent.toLowerCase())) {
        throw new Error(
          `Practice row not tied to loss opponent ${lossOpponent}.`,
        );
      }

      await page.click('[data-testid="game-detail-close"]');
      await page.waitForSelector('[data-testid="game-detail-modal"]', {
        hidden: true,
      });
    }

    const screenshotPath = await captureScreenshot(
      page,
      path.resolve(__dirname),
      SCREENSHOT_NAME,
    );
    console.log('Saved screenshot to', screenshotPath);

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }
  } catch (err) {
    if (page) {
      try {
        const failurePath = await captureScreenshot(
          page,
          path.resolve(__dirname),
          `failed-${SCREENSHOT_NAME}`,
        );
        console.error('Saved failure screenshot to', failurePath);
      } catch (screenshotErr) {
        console.error('Failed to capture failure screenshot:', screenshotErr);
      }
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Client E2E verification failed:', err);
    process.exit(1);
  } finally {
    if (browser) await browser.close();
    if (devServer) devServer.kill();
    if (backend) backend.kill();
  }
})();
