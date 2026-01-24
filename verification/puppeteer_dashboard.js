const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const puppeteer = require('puppeteer');

const CLIENT_DIR = path.resolve(__dirname, '..', 'client');
const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const SOURCE = process.env.TACTIX_SOURCE || 'lichess';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME || `dashboard-${SOURCE}.png`;

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

(async () => {
  console.log('Starting backend...');
  const backend = await startBackend();
  console.log('Starting preview server...');
  const server = await startPreview();
  try {
    console.log('Launching browser...');
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    console.log('Navigating to dashboard...');
    await page.goto('http://localhost:4173/', { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1');
    if (SOURCE === 'chesscom') {
        await page.$$eval(
          'button',
          (buttons, label) => {
            const target = buttons.find(
              (btn) => btn.textContent && btn.textContent.includes(label),
            );
            if (target) target.click();
          },
          'Chess.com',
        );
    }
    await page.$$eval(
      'button',
      (buttons, label) => {
        const target = buttons.find(
          (btn) => btn.textContent && btn.textContent.includes(label),
        );
        if (target) target.click();
      },
      'Run + Refresh',
    );
    await new Promise((resolve) => setTimeout(resolve, 2000));
    await page.waitForSelector('table');

    const outDir = path.resolve(__dirname);
    const outPath = path.join(outDir, SCREENSHOT_NAME);
    fs.mkdirSync(outDir, { recursive: true });
    await page.screenshot({ path: outPath, fullPage: true });
    console.log('Saved screenshot to', outPath);

    await browser.close();
  } finally {
    server.kill();
    backend.kill();
  }
})();
