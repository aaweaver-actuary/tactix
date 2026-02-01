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
const DASHBOARD_URL = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-231-outcome-unclear-discovered-check-2026-01-31.png';

function is_port__open(host, port, timeoutMs = 1000) {
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

function start_backend__server() {
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
          TACTIX_SOURCE: 'chesscom',
          TACTIX_USER: 'chesscom',
          TACTIX_CHESSCOM_PROFILE: 'blitz',
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

async function wait_for__dashboard_paint(delayMs = 1500) {
  await new Promise((resolve) => setTimeout(resolve, delayMs));
}

async function expand_card__by_title(page, title) {
  const headings = await page.$$('h3');
  const normalized = title.trim().toLowerCase();
  for (const heading of headings) {
    const text = await heading.evaluate((el) =>
      (el.textContent || '').trim().toLowerCase(),
    );
    if (text !== normalized) continue;
    const buttonHandle = await heading.evaluateHandle((el) =>
      el.closest('[role="button"]'),
    );
    const button = buttonHandle.asElement();
    if (!button) return;
    const expanded = await button.evaluate((el) =>
      el.getAttribute('aria-expanded'),
    );
    if (expanded === 'false') {
      await button.click();
    }
    return;
  }
}

(async () => {
  const backendRunning = await is_port__open('127.0.0.1', 8000);
  const backend = backendRunning ? null : await start_backend__server();
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

    await page.goto(DASHBOARD_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: 60000,
    });

    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]', {
      timeout: 60000,
    });

    await expand_card__by_title(page, 'Recent tactics');
    await wait_for__dashboard_paint(1000);

    await page.select('[data-testid="filter-chesscom-profile"]', 'blitz');
    await page.select('[data-testid="filter-time-control"]', 'all');
    await page.select('[data-testid="filter-motif"]', 'discovered_check');

    await wait_for__dashboard_paint(2000);

    const hasTableRow = await page.evaluate(() => {
      const headings = Array.from(document.querySelectorAll('h3'));
      const heading = headings.find(
        (node) =>
          (node.textContent || '').trim().toLowerCase() === 'recent tactics',
      );
      if (!heading) return false;
      const card = heading.closest('.card') || heading.closest('div');
      const table = card ? card.querySelector('table') : null;
      if (!table) return false;
      const rows = Array.from(table.querySelectorAll('tbody tr'));
      return rows.some((row) => {
        const text = (row.textContent || '').toLowerCase();
        return text.includes('unclear') && text.includes('discovered_check');
      });
    });
    if (!hasTableRow) {
      throw new Error(
        'Recent tactics table missing unclear discovered_check row',
      );
    }

    const screenshotPath = path.resolve(__dirname, SCREENSHOT_NAME);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    await browser.close();

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join(' | ')}`);
    }

    if (!fs.existsSync(screenshotPath)) {
      throw new Error(`Screenshot not created at ${screenshotPath}`);
    }

    console.log(`Saved screenshot to ${screenshotPath}`);
  } finally {
    if (backend) {
      backend.kill('SIGTERM');
    }
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
