const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const baseUrl = process.env.TACTIX_AIRFLOW_URL || 'http://localhost:8080';
const dagId = process.env.TACTIX_DAG_ID || 'monitor_new_positions';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  `feature-113-monitor-new-positions-${new Date().toISOString().slice(0, 10)}.png`;
const airflowUser = process.env.AIRFLOW_USERNAME || 'admin';
const airflowPass = process.env.AIRFLOW_PASSWORD || 'admin';

async function maybeLogin(page) {
  const loginField = await page.$('input[name="username"]');
  if (!loginField) return;
  await page.type('input[name="username"]', airflowUser, { delay: 30 });
  await page.type('input[name="password"]', airflowPass, { delay: 30 });
  const submit = await page.$(
    'button[type="submit"], input[type="submit"], button',
  );
  if (submit) {
    try {
      await submit.click();
    } catch (err) {
      await page.evaluate((el) => el.click(), submit);
    }
  } else {
    await page.keyboard.press('Enter');
  }
  try {
    await page.waitForNavigation({
      waitUntil: 'domcontentloaded',
      timeout: 15000,
    });
  } catch (err) {
    // ignore if no navigation occurs
  }
}

async function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(err.toString()));
  page.on('requestfailed', (request) => {
    const errorText = request.failure()?.errorText || 'unknown';
    if (errorText.includes('ERR_ABORTED')) return;
    consoleErrors.push(`Request failed: ${request.url()} (${errorText})`);
  });

  try {
    await page.goto(`${baseUrl}/dags/${dagId}/graph`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await delay(2000);
    await maybeLogin(page);
    await page.goto(`${baseUrl}/dags/${dagId}/graph`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await page.waitForSelector('svg', { timeout: 60000 });
    await delay(2000);

    const outDir = path.resolve(__dirname);
    const outPath = path.join(outDir, screenshotName);
    fs.mkdirSync(outDir, { recursive: true });
    await page.screenshot({ path: outPath, fullPage: true });
    console.log('Saved screenshot to', outPath);

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      throw new Error('Console errors detected during UI verification');
    }
  } finally {
    await browser.close();
  }
})();
