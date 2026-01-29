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
  process.env.TACTIX_SCREENSHOT_NAME || 'feature-game-detail-modal-2026-01-29.png';
const PYTHONPATH = [path.join(ROOT_DIR, 'src'), process.env.PYTHONPATH]
  .filter(Boolean)
  .join(path.delimiter);

function startBackend() {
  return new Promise((resolve, reject) => {
    let resolved = false;
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
        '--log-level',
        'info',
      ],
      {
        cwd: ROOT_DIR,
        env: { ...process.env, PYTHONPATH },
        stdio: ['ignore', 'pipe', 'pipe'],
      },
    );

    const onData = (data) => {
      const text = data.toString();
      if (
        text.includes('Uvicorn running') ||
        text.includes('Application startup complete')
      ) {
        cleanup();
        resolved = true;
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
      proc.off('close', onClose);
    }

    const onClose = (code) => {
      if (!resolved) {
        cleanup();
        reject(new Error(`Backend exited before ready (code ${code})`));
      }
    };

    proc.stdout.on('data', onData);
    proc.stderr.on('data', onData);
    proc.on('error', onError);
    proc.on('close', onClose);
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
      {
        stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env },
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

(async () => {
  console.log('Starting backend...');
  const backend = await startBackend();
  console.log('Backend ready.');
  console.log('Building client bundle...');
  await buildClient();
  console.log('Starting preview server...');
  const server = await startPreview();
  try {
    console.log('Launching browser...');
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

    console.log('Navigating to dashboard...');
    await page.goto('http://localhost:4173/', { waitUntil: 'networkidle0' });
    await page.waitForSelector('[data-testid="filter-source"]');
    await page.select('[data-testid="filter-source"]', 'lichess');
    await page.waitForSelector('[data-testid="action-run"]');
    await page.click('[data-testid="action-run"]');
    await new Promise((resolve) => setTimeout(resolve, 2000));
    await page.waitForSelector('[data-testid="dashboard-card-tactics-table"]');

    await page.click('[data-testid="dashboard-card-tactics-table"] [role="button"]');
    await page.waitForSelector(
      '[data-testid="dashboard-card-tactics-table"] [data-state]',
    );
    let expandedState = await page.$eval(
      '[data-testid="dashboard-card-tactics-table"] [data-state]',
      (el) => el.getAttribute('data-state') || 'unknown',
    );
    if (expandedState !== 'expanded') {
      await page.click('[data-testid="dashboard-card-tactics-table"] [role="button"]');
      await new Promise((resolve) => setTimeout(resolve, 300));
      expandedState = await page.$eval(
        '[data-testid="dashboard-card-tactics-table"] [data-state]',
        (el) => el.getAttribute('data-state') || 'unknown',
      );
    }

    await page.waitForSelector(
      '[data-testid="dashboard-card-tactics-table"] table tbody tr',
    );
    const firstRowText = await page.$eval(
      '[data-testid="dashboard-card-tactics-table"] table tbody tr',
      (el) => el.textContent || '',
    );
    if (firstRowText.toLowerCase().includes('no rows')) {
      throw new Error('No tactics rows found for lichess source');
    }
    for (let attempt = 0; attempt < 6; attempt += 1) {
      const rowText = await page.$eval(
        '[data-testid="dashboard-card-tactics-table"] table tbody tr',
        (el) => el.textContent || '',
      );
      const lower = rowText.toLowerCase();
      if (!lower.includes('loading') && !lower.includes('no rows')) {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
      if (attempt === 5) {
        throw new Error('Tactics table did not return any rows');
      }
    }
    await page.$eval(
      '[data-testid="dashboard-card-tactics-table"] table tbody tr',
      (el) => el.click(),
    );
    await page.waitForSelector('[data-testid="game-detail-modal"]', {
      visible: true,
    });
    await page.waitForSelector('[data-testid="game-detail-moves"]');

    const moveRows = await page.$$('[data-testid="game-move-row"]');
    if (moveRows.length === 0) {
      throw new Error('Expected move list rows in game detail modal');
    }

    const analysisText = await page.$eval(
      '[data-testid="game-detail-analysis"]',
      (el) => el.textContent || '',
    );
    const hasEval = analysisText.includes('Eval');
    const hasFlags =
      analysisText.includes('Flags') ||
      analysisText.includes('Blunder') ||
      analysisText.includes('OK');
    if (!hasEval || !hasFlags) {
      throw new Error('Expected analysis section to include eval and blunder checks');
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
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
