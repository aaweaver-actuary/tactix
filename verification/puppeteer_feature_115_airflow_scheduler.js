const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const baseUrl = process.env.TACTIX_AIRFLOW_URL || 'http://localhost:8080';
const dagId = process.env.TACTIX_DAG_ID || 'daily_game_sync';
const screenshotPrefix =
  process.env.TACTIX_SCREENSHOT_PREFIX ||
  `feature-115-airflow-scheduler-${new Date().toISOString().slice(0, 10)}`;
const airflowUser = process.env.AIRFLOW_USERNAME || 'admin';
const airflowPass = process.env.AIRFLOW_PASSWORD || 'admin';

async function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function maybeLogin(page) {
  const loginField = await page.$('input[name="username"]');
  if (!loginField) return;
  await page.type('input[name="username"]', airflowUser, { delay: 30 });
  await page.type('input[name="password"]', airflowPass, { delay: 30 });
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
  try {
    await page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 60000 });
  } catch (err) {
    // ignore if no navigation occurs
  }
}

async function dismissModal(page) {
  const modal = await page.$('div[role="dialog"], div[aria-modal="true"]');
  if (!modal) return;
  try {
    const closeButton = await page.$('button[aria-label="Close"], [aria-label="Close"]');
    if (closeButton) {
      await page.evaluate((el) => el.click(), closeButton);
      await delay(1000);
      return;
    }
    const buttons = await page.$$('button');
    for (const button of buttons) {
      const label = await page.evaluate((el) => (el.textContent || '').trim(), button);
      if (['OK', 'Close', 'Cancel', '×'].some((text) => label.includes(text))) {
        await button.click();
        await delay(1000);
        return;
      }
    }
  } catch (err) {
    // ignore modal dismissal issues
  }
}

async function ensureDagScheduling(page) {
  const result = await page.evaluate((targetDag) => {
    const table = document.querySelector('table');
    if (!table) return { found: false, reason: 'DAG table missing' };
    const headers = Array.from(table.querySelectorAll('thead th')).map((th) =>
      (th.textContent || '').trim().toLowerCase(),
    );
    const headerIndex = (names) =>
      headers.findIndex((text) => names.some((name) => text.includes(name)));

    const lastRunIndex = headerIndex(['last run', 'last']) ;
    const nextRunIndex = headerIndex(['next run', 'next']);
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    for (const row of rows) {
      const cells = Array.from(row.querySelectorAll('td')).map((cell) =>
        (cell.textContent || '').trim(),
      );
      if (cells.some((cell) => cell.includes(targetDag))) {
        const lastRun = lastRunIndex >= 0 ? cells[lastRunIndex] : '';
        const nextRun = nextRunIndex >= 0 ? cells[nextRunIndex] : '';
        return {
          found: true,
          lastRun,
          nextRun,
        };
      }
    }
    return { found: false, reason: `DAG ${targetDag} not found` };
  }, dagId);

  if (!result.found) {
    throw new Error(result.reason || `DAG ${dagId} not found in list`);
  }

  if (!result.lastRun || result.lastRun.toLowerCase() === 'none') {
    throw new Error(`DAG ${dagId} has no last run listed`);
  }

  if (!result.nextRun || result.nextRun.toLowerCase() === 'none') {
    throw new Error(`DAG ${dagId} has no next run listed`);
  }
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
    await dismissModal(page);
    await maybeLogin(page);
    await page.goto(`${baseUrl}/home`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('table', { timeout: 60000 });
    await delay(2000);

    await ensureDagScheduling(page);

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    await page.screenshot({
      path: path.join(outDir, `${screenshotPrefix}-dags.png`),
      fullPage: true,
    });

    await page.goto(`${baseUrl}/dags/${dagId}/grid`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await delay(3000);
    await dismissModal(page);
    await page.waitForSelector('table', { timeout: 60000 });

    await page.screenshot({
      path: path.join(outDir, `${screenshotPrefix}-runs.png`),
      fullPage: true,
    });

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('; ')}`);
    }
  } catch (err) {
    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, `${screenshotPrefix}-failed.png`);
    await page.screenshot({ path: outPath, fullPage: true });
    throw err;
  } finally {
    await browser.close();
  }
})();
