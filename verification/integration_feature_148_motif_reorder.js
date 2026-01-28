const net = require('net');
const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const DUCKDB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.join(ROOT_DIR, 'data', 'tactix.duckdb');
const DASHBOARD_URL = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const DASHBOARD_PARSED = new URL(DASHBOARD_URL);
const UI_HOST = DASHBOARD_PARSED.hostname || '127.0.0.1';
const UI_PORT = Number(DASHBOARD_PARSED.port || '5173');
const STORAGE_KEY = 'tactix.dashboard.motifCardOrder';

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
    [
      '--prefix',
      'client',
      'run',
      'dev',
      '--',
      '--host',
      '0.0.0.0',
      '--port',
      String(port),
    ],
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

async function getMotifOrder(page) {
  return page.$$eval('[data-motif-id]', (elements) =>
    elements.map((el) => el.getAttribute('data-motif-id')),
  );
}

(async () => {
  const backendRunning = await isPortOpen('127.0.0.1', 8000);
  const backend = backendRunning ? null : await startBackend();
  const frontendRunning = await isPortOpen(UI_HOST, UI_PORT);
  const frontend = frontendRunning ? null : await startFrontend(UI_PORT);
  let browser;
  let page;

  try {
    browser = await puppeteer.launch({ headless: 'new' });
    page = await browser.newPage();

    await page.goto(DASHBOARD_URL, {
      waitUntil: 'networkidle0',
      timeout: 60000,
    });
    await page.waitForSelector('[data-testid="motif-breakdown"]', {
      timeout: 60000,
    });

    const headerSelector =
      '[data-testid="motif-breakdown"] [role="button"]';
    const expandedValue = await page.$eval(headerSelector, (el) =>
      el.getAttribute('aria-expanded'),
    );
    if (expandedValue !== 'true') {
      await page.click(headerSelector);
      await page.waitForSelector(
        '[data-testid="motif-breakdown"] [data-state="expanded"]',
        { timeout: 60000 },
      );
    }

    await page.waitForSelector('[data-motif-id]', { timeout: 60000 });

    const initialOrder = await getMotifOrder(page);
    if (!initialOrder.length || initialOrder.length < 2) {
      throw new Error('Need at least two motif cards to reorder');
    }

    const sourceIndex = 0;
    const targetIndex = initialOrder.length - 1;
    const sourceId = initialOrder[sourceIndex];
    if (!sourceId) {
      throw new Error('No motif id found for reorder');
    }

    const dragHandleSelector =
      `[data-motif-id="${sourceId}"] [aria-label="Reorder ${sourceId}"]`;
    await page.waitForSelector(dragHandleSelector, { timeout: 60000 });
    await page.focus(dragHandleSelector);
    await page.keyboard.press('Space');

    for (let i = 0; i < targetIndex; i += 1) {
      // eslint-disable-next-line no-await-in-loop
      await page.keyboard.press('ArrowDown');
    }

    await page.keyboard.press('Space');

    await page.waitForFunction(
      (previousOrder) => {
        const current = Array.from(
          document.querySelectorAll('[data-motif-id]'),
        ).map((el) => el.getAttribute('data-motif-id'));
        return current.join('|') !== previousOrder.join('|');
      },
      { timeout: 60000 },
      initialOrder,
    );

    const storedOrderRaw = await page.evaluate(
      (key) => localStorage.getItem(key),
      STORAGE_KEY,
    );
    if (!storedOrderRaw) {
      throw new Error('Expected motif order to be stored in localStorage');
    }
    const storedOrder = JSON.parse(storedOrderRaw);
    if (!Array.isArray(storedOrder)) {
      throw new Error('Stored motif order is not an array');
    }
    if (!storedOrder.includes(sourceId)) {
      throw new Error('Stored motif order missing reordered motif');
    }

    console.log('Feature 148 integration check ok');
  } catch (err) {
    console.error('Feature 148 integration check failed:', err);
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
