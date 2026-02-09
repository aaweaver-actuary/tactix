const path = require('path');
const { spawn } = require('child_process');

const RUN_DATE = '2026-02-01';

function buildClientE2EConfig({
  baseDir,
  backendPortDefault,
  uiPortDefault,
  duckdbFileName,
  screenshotNameDefault,
}) {
  const rootDir = path.resolve(baseDir, '..');
  const clientDir = path.resolve(rootDir, 'client');
  const backendCmd = path.join(rootDir, '.venv', 'bin', 'python');
  const backendPort = process.env.TACTIX_BACKEND_PORT || backendPortDefault;
  const devServerPort = process.env.TACTIX_UI_PORT || uiPortDefault;
  const apiBase = process.env.TACTIX_API_BASE || `http://localhost:${backendPort}`;
  const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
  const targetUrl =
    process.env.TACTIX_UI_URL || `http://localhost:${devServerPort}/`;
  const backendRunning = process.env.TACTIX_BACKEND_RUNNING === '1';
  const testUser = (
    process.env.TACTIX_TEST_CHESSCOM_USER || 'groborger'
  ).toLowerCase();
  const duckdbPath =
    process.env.TACTIX_DUCKDB_PATH ||
    path.resolve(rootDir, 'tmp-logs', duckdbFileName);
  const screenshotName = screenshotNameDefault
    ? process.env.TACTIX_SCREENSHOT_NAME || screenshotNameDefault
    : undefined;

  return {
    rootDir,
    clientDir,
    backendCmd,
    backendPort,
    devServerPort,
    apiBase,
    apiToken,
    targetUrl,
    backendRunning,
    testUser,
    duckdbPath,
    screenshotName,
    runDate: RUN_DATE,
  };
}

function getPracticeQueueLimitEnv() {
  return process.env.VITE_PRACTICE_QUEUE_LIMIT || '2';
}

function startDevServer({ clientDir, devServerPort, apiBase }) {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      'npm',
      [
        '--prefix',
        clientDir,
        'run',
        'dev',
        '--',
        '--host',
        '--port',
        devServerPort,
        '--strictPort',
      ],
      {
        stdio: ['ignore', 'pipe', 'pipe'],
        env: {
          ...process.env,
          VITE_API_BASE: apiBase,
          VITE_PRACTICE_QUEUE_LIMIT: getPracticeQueueLimitEnv(),
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

function launchBackend({
  rootDir,
  backendCmd,
  backendPort,
  apiToken,
  duckdbPath,
  testUser,
}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      backendCmd,
      ['-m', 'uvicorn', 'tactix.api:app', '--host', '0.0.0.0', '--port', backendPort],
      {
        cwd: rootDir,
        env: {
          ...process.env,
          TACTIX_API_TOKEN: apiToken,
          TACTIX_SOURCE: 'chesscom',
          TACTIX_USER: testUser,
          TACTIX_CHESSCOM_PROFILE: 'bullet',
          TACTIX_CHESSCOM_USE_FIXTURE: '1',
          TACTIX_USE_FIXTURE: '1',
          TACTIX_DUCKDB_PATH: duckdbPath,
          CHESSCOM_USERNAME: testUser,
          CHESSCOM_USER: testUser,
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
  await openFiltersModal(page);
}

async function openFiltersModal(page) {
  const modalSelector = '[data-testid="filters-modal"]';
  if (await page.$(modalSelector)) return;
  await page.waitForSelector('[data-testid="filters-open"]', {
    timeout: 60000,
  });
  await page.click('[data-testid="filters-open"]');
  await page.waitForSelector(modalSelector, { timeout: 60000 });
  await page.waitForFunction(
    () => Boolean(document.querySelector('[data-testid="filter-source"]')),
    { timeout: 60000 },
  );
}

async function closeFiltersModal(page) {
  const modalSelector = '[data-testid="filters-modal"]';
  if (!(await page.$(modalSelector))) return;
  const closeButton = await page.$('[data-testid="filters-modal-close"]');
  if (closeButton) {
    await closeButton.click();
  } else {
    await page.click(modalSelector);
  }
  await page.waitForFunction(
    (selector) => !document.querySelector(selector),
    { timeout: 60000 },
    modalSelector,
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

async function applyFilters(page, runDate) {
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

  await setDateInput(page, '[data-testid="filter-start-date"]', runDate);
  await setDateInput(page, '[data-testid="filter-end-date"]', runDate);
  await closeFiltersModal(page);
}

async function step(label, fn) {
  try {
    return await fn();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`${label} failed: ${message}`);
  }
}

module.exports = {
  applyFilters,
  buildClientE2EConfig,
  ensureCardExpanded,
  ensureFiltersExpanded,
  closeFiltersModal,
  getPracticeQueueLimitEnv,
  launchBackend,
  openFiltersModal,
  RUN_DATE,
  setDateInput,
  startDevServer,
  step,
};
