const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const uiBase = process.env.TACTIX_UI_URL || 'http://localhost:5173';
const airflowBase = process.env.TACTIX_AIRFLOW_URL || 'http://localhost:8080';
const airflowUser = process.env.AIRFLOW_USERNAME || 'admin';
const airflowPass = process.env.AIRFLOW_PASSWORD || 'admin';
const runDate = new Date().toISOString().slice(0, 10);
const outDir = path.resolve(__dirname);

const screenshots = {
  uiStart: `feature-012-sse-ui-start-${runDate}.png`,
  uiProgress: `feature-012-sse-ui-progress-${runDate}.png`,
  uiComplete: `feature-012-sse-ui-complete-${runDate}.png`,
  uiPractice: `feature-012-sse-ui-practice-${runDate}.png`,
  airflow: `feature-012-sse-airflow-${runDate}.png`,
};

async function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function clickByText(page, selector, text) {
  const handles = await page.$$(selector);
  for (const handle of handles) {
    const label = await page.evaluate((el) => el.textContent || '', handle);
    if (label.trim() === text) {
      await handle.click();
      return true;
    }
  }
  return false;
}

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

async function getMetricsVersion(page) {
  return page.evaluate(() => {
    const text = document.body?.innerText || '';
    const match = text.match(/metrics version\s+(\d+)/i);
    return match ? Number(match[1]) : null;
  });
}

async function getJobProgressText(page) {
  return page.evaluate(() => {
    const header = Array.from(document.querySelectorAll('h3')).find((el) =>
      (el.textContent || '').includes('Job progress'),
    );
    if (!header) return '';
    const card = header.closest('.card') || header.parentElement?.parentElement;
    if (!card) return header.parentElement?.innerText || '';
    return card.innerText || '';
  });
}

async function getPracticeBestMove(page) {
  return page.evaluate(() => {
    const header = Array.from(document.querySelectorAll('h3')).find((el) =>
      (el.textContent || '').includes('Practice attempt'),
    );
    if (!header) return null;
    const card = header.closest('.card') || header.parentElement?.parentElement;
    if (!card) return null;
    const badges = Array.from(card.querySelectorAll('span')).map((el) =>
      (el.textContent || '').trim(),
    );
    const best = badges.find((label) => label.startsWith('Best '));
    return best ? best.replace('Best ', '').trim() : null;
  });
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', protocolTimeout: 900000 });
  const page = await browser.newPage();
  page.setDefaultTimeout(900000);
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

  const verificationErrors = [];
  let jobFailed = false;
  try {
    fs.mkdirSync(outDir, { recursive: true });
    await page.goto(uiBase, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('button', { timeout: 60000 });
    await delay(1000);

    const clicked = await clickByText(page, 'button', 'Chess.com · Blitz');
    assert(clicked, 'Failed to select Chess.com source');
    await page.waitForFunction(
      () => document.querySelector('h1')?.textContent?.toLowerCase().includes('chess.com'),
      { timeout: 30000 },
    );

    const metricsBefore = await getMetricsVersion(page);
    await page.screenshot({
      path: path.join(outDir, screenshots.uiStart),
      fullPage: true,
    });

    await page.click('[data-testid="action-run"]');
    await page.waitForFunction(
      () => Array.from(document.querySelectorAll('h3')).some((el) =>
        (el.textContent || '').includes('Job progress'),
      ),
      { timeout: 60000 },
    );

    await delay(1500);
    await page.screenshot({
      path: path.join(outDir, screenshots.uiProgress),
      fullPage: true,
    });

    await page.waitForFunction(
      () => {
        const header = Array.from(document.querySelectorAll('h3')).find((el) =>
          (el.textContent || '').includes('Job progress'),
        );
        const card = header?.closest('.card') || header?.parentElement?.parentElement;
        const text = card?.innerText || '';
        return text.includes('metrics_refreshed') || text.includes('Error');
      },
      { timeout: 900000 },
    );

    await delay(1000);
    await page.screenshot({
      path: path.join(outDir, screenshots.uiComplete),
      fullPage: true,
    });

    const jobText = await getJobProgressText(page);
    const jobLogPath = path.join(outDir, `feature-012-sse-job-progress-${runDate}.txt`);
    fs.writeFileSync(jobLogPath, jobText);
    if (jobText.includes('Error')) {
      console.error('Job progress error detected:\n', jobText);
      verificationErrors.push('Job progress reported an error state');
      jobFailed = true;
    }
    const requiredSteps = [
      'start',
      'fetch_games',
      'raw_pgns',
      'raw_pgns_persisted',
      'extract_positions',
      'positions_ready',
      'analyze_positions',
      'metrics_refreshed',
    ];
    for (const step of requiredSteps) {
      if (!jobText.includes(step)) {
        verificationErrors.push(`Missing job progress step: ${step}`);
      }
    }

    const metricsAfter = await getMetricsVersion(page);
    if (metricsAfter === null) {
      verificationErrors.push('Metrics version not visible after run');
    }

    const tacticsRows = await page.$$('[data-testid^="dashboard-game-row-"]');
    if (tacticsRows.length === 0) {
      verificationErrors.push('Expected recent tactics rows after run');
    }

    if (!jobFailed) {
      const bestMove = await getPracticeBestMove(page);
      if (!bestMove) {
        verificationErrors.push('No practice queue item available for explanation check');
      } else {
        const moveInput = await page.$('input[placeholder^="Enter your move"]');
        if (!moveInput) {
          verificationErrors.push('Practice move input not found');
        } else {
          await moveInput.click({ clickCount: 3 });
          await moveInput.type(bestMove, { delay: 40 });
          const submitted = await clickByText(page, 'button', 'Submit attempt');
          if (!submitted) {
            verificationErrors.push('Submit attempt button not found');
          } else {
            await page.waitForFunction(
              () => Array.from(document.querySelectorAll('div')).some((el) =>
                (el.textContent || '').includes('Correct') || (el.textContent || '').includes('Missed'),
              ),
              { timeout: 60000 },
            );

            await page.waitForFunction(
              () => {
                const header = Array.from(document.querySelectorAll('h3')).find((el) =>
                  (el.textContent || '').includes('Practice attempt'),
                );
                if (!header) return false;
                const card = header.closest('.card') || header.parentElement?.parentElement;
                if (!card) return false;
                const feedbackBlock = Array.from(card.querySelectorAll('div')).find((el) =>
                  (el.textContent || '').includes('Correct') ||
                  (el.textContent || '').includes('Missed'),
                );
                if (!feedbackBlock) return false;
                const paragraphs = Array.from(feedbackBlock.querySelectorAll('p')).filter((p) =>
                  (p.textContent || '').trim().length > 0,
                );
                return paragraphs.length >= 2;
              },
              { timeout: 60000 },
            );
            await page.screenshot({
              path: path.join(outDir, screenshots.uiPractice),
              fullPage: true,
            });
          }
        }
      }
    }

    if (consoleErrors.length) {
      verificationErrors.push(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    const airflowPage = await browser.newPage();
    await airflowPage.goto(`${airflowBase}/home`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await delay(1500);
    await maybeLogin(airflowPage);

    await airflowPage.goto(`${airflowBase}/dags/daily_game_sync/grid`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await airflowPage.waitForSelector('body', { timeout: 60000 });
    await delay(2000);

    const stillOnLogin = await airflowPage.$('input[name="username"], input[name="password"]');
    if (stillOnLogin) {
      throw new Error('Airflow DAG grid is not accessible after login');
    }

    await airflowPage.screenshot({
      path: path.join(outDir, screenshots.airflow),
      fullPage: true,
    });

    const airflowText = await airflowPage.evaluate(() => document.body?.innerText || '');
    if (!airflowText.includes(runDate)) {
      verificationErrors.push(`Expected Airflow run date ${runDate} not found`);
    }
    const statusKeywords = ['queued', 'running', 'success', 'failed'];
    if (!statusKeywords.some((keyword) => airflowText.toLowerCase().includes(keyword))) {
      verificationErrors.push('Expected Airflow status (queued/running/success/failed) not found');
    }

    if (metricsBefore !== null && metricsAfter !== null && metricsAfter < metricsBefore) {
      verificationErrors.push('Metrics version did not update');
    }
    if (verificationErrors.length) {
      throw new Error(verificationErrors.join('\n'));
    }
  } catch (err) {
    console.error(err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
