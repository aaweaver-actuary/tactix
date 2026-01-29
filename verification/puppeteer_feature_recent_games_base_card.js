const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');

const CLIENT_DIR = path.resolve(__dirname, '..', 'client');
const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const API_PORT = Number(process.env.TACTIX_API_PORT || '8000');
const API_BASE = `http://localhost:${API_PORT}`;
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  `feature-recent-games-2026-01-29.png`;

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
        String(API_PORT),
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

function buildClient() {
  return new Promise((resolve, reject) => {
    const proc = spawn('npm', ['--prefix', CLIENT_DIR, 'run', 'build'], {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, VITE_API_BASE: API_BASE },
    });

    proc.on('error', reject);
    proc.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Client build failed with exit code ${code}`));
      }
    });
  });
}

function startPreview() {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      'npm',
      [
        '--prefix',
        CLIENT_DIR,
        'run',
        'preview',
        '--',
        '--host',
        '--port',
        '4173',
      ],
      { stdio: ['ignore', 'pipe', 'pipe'] },
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

async function waitForHeader(root, label) {
  const headers = await root.$$('th');
  for (const header of headers) {
    const textHandle = await header.getProperty('textContent');
    const text = await textHandle.jsonValue();
    if (String(text || '').includes(label)) {
      return;
    }
  }
  throw new Error(`Missing header: ${label}`);
}

async function getRowCells(rowHandle) {
  const cells = await rowHandle.$$('td');
  const values = [];
  for (const cell of cells) {
    const textHandle = await cell.getProperty('textContent');
    const text = await textHandle.jsonValue();
    values.push(String(text || '').trim());
  }
  return values;
}

async function clickNextPage(root) {
  const buttons = await root.$$('button');
  for (const button of buttons) {
    const textHandle = await button.getProperty('textContent');
    const text = String((await textHandle.jsonValue()) || '').trim();
    if (text === 'Next') {
      const disabledHandle = await button.getProperty('disabled');
      const disabled = Boolean(await disabledHandle.jsonValue());
      if (disabled) return false;
      await button.click();
      await new Promise((resolve) => setTimeout(resolve, 300));
      return true;
    }
  }
  return false;
}

async function waitForDataRows(root, timeoutMs = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const rows = await root.$$('tbody tr');
    for (const row of rows) {
      const cells = await getRowCells(row);
      if (cells.length >= 4) {
        const firstCell = String(cells[0] || '').toLowerCase();
        if (
          firstCell &&
          !firstCell.includes('loading') &&
          !firstCell.includes('no rows')
        ) {
          return;
        }
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error('No recent game data rows loaded.');
}

(async () => {
  console.log('Starting backend...');
  const backend = await startBackend();
  console.log('Starting preview server...');
  const server = await startPreview();
  try {
    console.log('Launching browser...');
    console.log('Building client bundle...');
    await buildClient();
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
    await page.goto('http://localhost:4173/', { waitUntil: 'networkidle0' });
    await page.waitForSelector('[data-testid="filter-source"]');
    await page.waitForSelector('[data-testid="recent-games-card"]');
    const card = await page.$('[data-testid="recent-games-card"]');
    if (!card) {
      throw new Error('Recent games card not found.');
    }

    const headerButton = await card.$('[role="button"]');
    if (headerButton) {
      await headerButton.click();
    }

    await waitForHeader(card, 'Opponent');
    await waitForHeader(card, 'Result');
    await waitForHeader(card, 'Date');

    await waitForDataRows(card);

    let chesscomCells = null;
    let lichessCells = null;
    for (let pageIndex = 0; pageIndex < 10; pageIndex += 1) {
      const rows = await card.$$('tbody tr');
      for (const row of rows) {
        const cells = await getRowCells(row);
        if (cells.length < 4) continue;
        const sourceValue = String(cells[0] || '').toLowerCase();
        if (!chesscomCells && sourceValue.includes('chesscom')) {
          chesscomCells = cells;
        }
        if (!lichessCells && sourceValue.includes('lichess')) {
          lichessCells = cells;
        }
      }

      if (chesscomCells && lichessCells) break;

      const moved = await clickNextPage(card);
      if (!moved) break;
    }

    if (!chesscomCells || !lichessCells) {
      throw new Error('Missing chesscom or lichess recent game rows.');
    }

    if (chesscomCells.length < 4 || lichessCells.length < 4) {
      throw new Error('Recent games rows do not contain enough columns.');
    }

    if (!chesscomCells[1] || !chesscomCells[2] || !chesscomCells[3]) {
      throw new Error('Chess.com row missing opponent, result, or date values.');
    }

    if (!lichessCells[1] || !lichessCells[2] || !lichessCells[3]) {
      throw new Error('Lichess row missing opponent, result, or date values.');
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
    server.kill();
    backend.kill();
  }
})();
