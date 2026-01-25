const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const net = require('net');
const puppeteer = require(path.join(
  path.resolve(__dirname, '..'),
  'client',
  'node_modules',
  'puppeteer',
));

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const CLIENT_DIR = path.join(ROOT_DIR, 'client');
const DASHBOARD_URL =
  process.env.TACTIX_DASHBOARD_URL || 'http://localhost:5173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-025a-chesscom-env-2026-01-25.png';
const RUN_BUTTON_SELECTOR =
  process.env.TACTIX_RUN_SELECTOR || 'button.button.bg-teal.font-display';
const FRONTEND_HOST = '127.0.0.1';
const FRONTEND_PORT = 5173;
function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  const raw = fs.readFileSync(filePath, 'utf-8');
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const idx = trimmed.indexOf('=');
    if (idx === -1) continue;
    const key = trimmed.slice(0, idx).trim();
    const value = trimmed.slice(idx + 1).trim();
    if (!Object.prototype.hasOwnProperty.call(process.env, key)) {
      process.env[key] = value;
    }
  }
}

loadEnvFile(path.join(ROOT_DIR, '.env'));

const CHESSCOM_USERNAME = process.env.CHESSCOM_USERNAME || 'unknown';

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
  console.log('Starting backend...');
  const backend = await startBackend();
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
    const clickedSource = await page.$$eval('button', (nodes) => {
      const target = nodes.find((node) =>
        (node.textContent || '').includes('Chess.com'),
      );
      if (target) {
        target.click();
        return true;
      }
      return false;
    });
    if (!clickedSource) {
      await page.select('[data-testid="filter-source"]', 'chesscom');
    }
    await page.evaluate(() => {
      const select = document.querySelector('[data-testid="filter-source"]');
      if (!select) return;
      if (select.value !== 'chesscom') {
        select.value = 'chesscom';
        select.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
    await page.waitForResponse(
      (response) => {
        const url = response.url();
        return (
          url.includes('/api/dashboard') &&
          url.includes('source=chesscom') &&
          response.status() === 200
        );
      },
      { timeout: 60000 },
    );
    await page.waitForSelector(RUN_BUTTON_SELECTOR);
    await page.click(RUN_BUTTON_SELECTOR);
    await page.waitForSelector('table');

    await page.waitForSelector('p');
    const heroText = await page.$$eval('p', (nodes) => {
      const match = nodes.find((node) =>
        (node.textContent || '').includes('Execution stamped via metrics version'),
      );
      return match ? match.textContent || '' : '';
    });
    const normalizedHero = heroText.toLowerCase();
    const expected = `user ${CHESSCOM_USERNAME}`.toLowerCase();
    if (!normalizedHero.includes(expected)) {
      throw new Error(
        `Expected hero text to include ${expected}, got: ${heroText || 'empty'}`,
      );
    }

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
