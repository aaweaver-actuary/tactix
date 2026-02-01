const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const uiBase = process.env.TACTIX_UI_URL || 'http://localhost:5173';
const airflowBase = process.env.TACTIX_AIRFLOW_URL || 'http://localhost:8080';
const airflowUser = process.env.AIRFLOW_USERNAME || 'admin';
const airflowPass = process.env.AIRFLOW_PASSWORD || 'admin';
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const outDir = path.resolve(__dirname);

const shots = {
  uiStart: `feature-012-rerun-ui-start-${stamp}.png`,
  uiProgress: `feature-012-rerun-ui-progress-${stamp}.png`,
  uiProgressTimeout: `feature-012-rerun-ui-progress-timeout-${stamp}.png`,
  uiTimeout: `feature-012-rerun-ui-timeout-${stamp}.png`,
  airflow: `feature-012-rerun-airflow-${stamp}.png`,
};

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function maybeLogin(page) {
  const loginField = await page.$('input[name="username"]');
  if (!loginField) return;
  await page.type('input[name="username"]', airflowUser, { delay: 20 });
  await page.type('input[name="password"]', airflowPass, { delay: 20 });
  const btn = await page.$(
    'button[type="submit"], input[type="submit"], button',
  );
  if (btn) {
    await btn.click();
  } else {
    await page.keyboard.press('Enter');
  }
  await page.waitForNavigation({
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
}

async function getJobProgressText(page) {
  return page.evaluate(() => {
    const header = Array.from(document.querySelectorAll('h3')).find((el) =>
      (el.textContent || '').includes('Job progress'),
    );
    const card =
      header?.closest('.card') || header?.parentElement?.parentElement;
    return card?.innerText || '';
  });
}

async function captureAirflowGrid(browser, outDir, shotPath) {
  const airflowPage = await browser.newPage();
  await airflowPage.goto(`${airflowBase}/home`, {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await delay(1500);
  await maybeLogin(airflowPage);
  await airflowPage.goto(`${airflowBase}/dags/daily_game_sync/grid`, {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await airflowPage.waitForSelector('body', { timeout: 60000 });
  await delay(1500);
  await airflowPage.screenshot({
    path: path.join(outDir, shotPath),
    fullPage: true,
  });
  await airflowPage.close();
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await puppeteer.launch({
    headless: 'new',
    protocolTimeout: 300000,
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(300000);

  try {
    await page.goto(uiBase, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('button', { timeout: 60000 });

    await page.waitForSelector('[data-testid="filter-source"]', {
      timeout: 60000,
    });
    await page.select('[data-testid="filter-source"]', 'chesscom');
    await page.waitForSelector('[data-testid="filter-chesscom-profile"]', {
      timeout: 60000,
    });
    await page.select('[data-testid="filter-chesscom-profile"]', 'blitz');

    const runButton = await page.$('[data-testid="action-run"]');
    if (!runButton)
      throw new Error(
        'Run button not available after selecting Chess.com · Blitz',
      );
    await delay(1000);

    await page.screenshot({
      path: path.join(outDir, shots.uiStart),
      fullPage: true,
    });

    await page.click('[data-testid="action-run"]');
    try {
      await page.waitForFunction(
        () =>
          Array.from(document.querySelectorAll('h3')).some((el) =>
            (el.textContent || '').includes('Job progress'),
          ),
        { timeout: 60000 },
      );
    } catch (err) {
      await page.screenshot({
        path: path.join(outDir, shots.uiProgressTimeout),
        fullPage: true,
      });
      throw err;
    }

    await delay(1500);
    await page.screenshot({
      path: path.join(outDir, shots.uiProgress),
      fullPage: true,
    });

    let jobText = '';
    try {
      await page.waitForFunction(
        () => {
          const header = Array.from(document.querySelectorAll('h3')).find(
            (el) => (el.textContent || '').includes('Job progress'),
          );
          const card =
            header?.closest('.card') || header?.parentElement?.parentElement;
          const text = card?.innerText || '';
          return text.includes('metrics_refreshed') || text.includes('Error');
        },
        { timeout: 180000 },
      );
    } catch (err) {
      jobText = await getJobProgressText(page);
      fs.writeFileSync(
        path.join(outDir, `feature-012-rerun-job-progress-${stamp}.txt`),
        jobText,
      );
      await page.screenshot({
        path: path.join(outDir, shots.uiTimeout),
        fullPage: true,
      });
      await captureAirflowGrid(browser, outDir, shots.airflow);
      throw new Error(
        'Job progress did not reach metrics_refreshed within 3 minutes',
      );
    }

    jobText = await getJobProgressText(page);
    fs.writeFileSync(
      path.join(outDir, `feature-012-rerun-job-progress-${stamp}.txt`),
      jobText,
    );
    await captureAirflowGrid(browser, outDir, shots.airflow);

    console.log('Feature 012 rerun ok');
  } catch (err) {
    console.error(err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
