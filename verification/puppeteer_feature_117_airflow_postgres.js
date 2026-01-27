const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const baseUrl = process.env.TACTIX_AIRFLOW_URL || 'http://localhost:8080';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  `feature-117-airflow-postgres-${new Date().toISOString().slice(0, 10)}.png`;
const airflowUser = process.env.AIRFLOW_USERNAME || 'admin';
const airflowPass = process.env.AIRFLOW_PASSWORD || 'admin';

async function maybeLogin(page) {
  const loginField = await page.$('input[name="username"]');
  if (!loginField) return;
  await page.type('input[name="username"]', airflowUser, { delay: 25 });
  await page.type('input[name="password"]', airflowPass, { delay: 25 });
  const submitSelectors = [
    'button[type="submit"]',
    'input[type="submit"]',
    'button[data-testid="login"]',
    'button',
  ];
  let submitted = false;
  for (const selector of submitSelectors) {
    const handle = await page.$(selector);
    if (handle) {
      await handle.click();
      submitted = true;
      break;
    }
  }
  if (!submitted) {
    await page.keyboard.press('Enter');
  }
  await page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 60000 });
}

async function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', protocolTimeout: 120000 });
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
    await page.goto(`${baseUrl}/home`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await delay(2000);
    await maybeLogin(page);

    await page.goto(`${baseUrl}/configuration`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('body', { timeout: 60000 });
    await delay(1500);

    const stillOnLogin = await page.$('input[name="username"], input[name="password"]');
    if (stillOnLogin) {
      throw new Error('Airflow configuration page is not accessible after login');
    }

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    await page.screenshot({
      path: path.join(outDir, screenshotName),
      fullPage: true,
    });

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }
  } catch (err) {
    console.error(err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
