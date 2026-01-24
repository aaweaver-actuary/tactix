const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const puppeteer = require('puppeteer');

const CLIENT_DIR = path.resolve(__dirname, '..', 'client');

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
  const server = await startPreview();
  try {
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    await page.goto('http://localhost:4173/', { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1');
    await page.click('button.button');
    await new Promise((resolve) => setTimeout(resolve, 2000));
    await page.waitForSelector('table');

    const outDir = path.resolve(__dirname);
    const outPath = path.join(outDir, 'feature001-dashboard.png');
    fs.mkdirSync(outDir, { recursive: true });
    await page.screenshot({ path: outPath, fullPage: true });
    console.log('Saved screenshot to', outPath);

    await browser.close();
  } finally {
    server.kill();
  }
})();
