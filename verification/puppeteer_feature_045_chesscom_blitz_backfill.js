const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('../client/node_modules/puppeteer');

const CLIENT_DIR = path.resolve(__dirname, '..', 'client');
const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-045-chesscom-blitz-backfill-2026-01-25.png';

const getMetricValue = async (page, title) => {
  return page.$$eval(
    'div.card',
    (cards, label) => {
      const match = cards.find((card) => {
        const titleEl =
          card.querySelector('p.text-sm') || card.querySelector('p.text-xs');
        return titleEl && titleEl.textContent?.trim() === label;
      });
      if (!match) return null;
      const valueEl = match.querySelector('p.text-3xl');
      return valueEl ? valueEl.textContent?.trim() : null;
    },
    title,
  );
};

const clickButtonByText = async (page, label) => {
  await page.$$eval(
    'button',
    (buttons, targetLabel) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes(targetLabel),
      );
      if (target) target.click();
    },
    label,
  );
};

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

function startFrontend() {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      'npm',
      ['--prefix', CLIENT_DIR, 'run', 'dev', '--', '--host', '--port', '5173'],
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

(async () => {
  const backend = await startBackend();
  const preview = await startFrontend();
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

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: 60000,
    });
    await page.waitForFunction(
      () => !document.querySelector('[data-testid="filter-source"]')?.disabled,
      { timeout: 60000 },
    );

    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForFunction(
      () =>
        document.querySelector('[data-testid="filter-source"]')?.value ===
        'chesscom',
      { timeout: 60000 },
    );
    await page.waitForFunction(
      () =>
        Boolean(
          document.querySelector('[data-testid="filter-chesscom-profile"]'),
        ),
      { timeout: 60000 },
    );
    await page.select('[data-testid="filter-chesscom-profile"]', 'blitz');

    await page.waitForSelector('button', { timeout: 60000 });
    await page.waitForSelector('[data-testid="motif-breakdown"]', {
      timeout: 120000,
    });
    await page.waitForSelector('table');

    const positionsBefore = await getMetricValue(page, 'Positions');
    const tacticsBefore = await getMetricValue(page, 'Tactics');

    await clickButtonByText(page, 'Backfill history');
    await page.waitForSelector('[data-testid="motif-breakdown"]', {
      timeout: 120000,
    });
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const positionsAfterFirst = await getMetricValue(page, 'Positions');
    const tacticsAfterFirst = await getMetricValue(page, 'Tactics');

    await clickButtonByText(page, 'Backfill history');
    await page.waitForSelector('[data-testid="motif-breakdown"]', {
      timeout: 120000,
    });
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const positionsAfterSecond = await getMetricValue(page, 'Positions');
    const tacticsAfterSecond = await getMetricValue(page, 'Tactics');

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });

    if (
      positionsBefore !== positionsAfterFirst ||
      tacticsBefore !== tacticsAfterFirst ||
      positionsAfterFirst !== positionsAfterSecond ||
      tacticsAfterFirst !== tacticsAfterSecond
    ) {
      throw new Error(
        `Backfill changed counts: positions ${positionsBefore} -> ${positionsAfterFirst} -> ${positionsAfterSecond}, ` +
          `tactics ${tacticsBefore} -> ${tacticsAfterFirst} -> ${tacticsAfterSecond}`,
      );
    }

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
  } catch (err) {
    try {
      const outDir = path.resolve(__dirname);
      fs.mkdirSync(outDir, { recursive: true });
      const outPath = path.join(outDir, `failed-${screenshotName}`);
      await page.screenshot({ path: outPath, fullPage: true });
      console.error('Saved failure screenshot to', outPath);
      const htmlPath = path.join(
        outDir,
        'failed-feature-045-chesscom-blitz-backfill-debug.html',
      );
      const html = await page.content();
      fs.writeFileSync(htmlPath, html);
      console.error('Saved failure HTML to', htmlPath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Feature 045 verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
    preview.kill();
    backend.kill();
  }
})();
