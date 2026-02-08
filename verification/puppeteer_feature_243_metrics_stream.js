const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const uiBase = process.env.TACTIX_UI_URL || 'http://localhost:5173';
const runDate = new Date().toISOString().slice(0, 10);
const outDir = path.resolve(__dirname);

const screenshots = {
  before: `feature-243-metrics-stream-before-${runDate}.png`,
  after: `feature-243-metrics-stream-after-${runDate}.png`,
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

async function getMetricsVersion(page) {
  return page.evaluate(() => {
    const text = document.body?.innerText || '';
    const match = text.match(/metrics version\s+(\d+)/i);
    return match ? Number(match[1]) : null;
  });
}

async function getNavigationType(page) {
  return page.evaluate(() => {
    const entries = performance.getEntriesByType('navigation');
    if (!entries.length) return 'unknown';
    return entries[0].type || 'unknown';
  });
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    protocolTimeout: 900000,
  });
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
  try {
    fs.mkdirSync(outDir, { recursive: true });
    await page.goto(uiBase, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('button', { timeout: 60000 });
    await delay(1000);

    const clicked = await clickByText(page, 'button', 'Chess.com · Blitz');
    assert(clicked, 'Failed to select Chess.com source');
    await page.waitForFunction(
      () =>
        document
          .querySelector('h1')
          ?.textContent?.toLowerCase()
          .includes('chess.com'),
      { timeout: 30000 },
    );

    const navTypeBefore = await getNavigationType(page);
    const versionBefore = await getMetricsVersion(page);
    if (versionBefore === null) {
      verificationErrors.push('Metrics version not visible before refresh');
    }

    await page.screenshot({
      path: path.join(outDir, screenshots.before),
      fullPage: true,
    });

    await page.click('[data-testid="action-refresh"]');

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
      path: path.join(outDir, screenshots.after),
      fullPage: true,
    });

    const navTypeAfter = await getNavigationType(page);
    const versionAfter = await getMetricsVersion(page);
    if (versionAfter === null) {
      verificationErrors.push('Metrics version not visible after refresh');
    }
    if (
      versionBefore !== null &&
      versionAfter !== null &&
      Number.isFinite(versionBefore) &&
      Number.isFinite(versionAfter) &&
      versionAfter < versionBefore
    ) {
      verificationErrors.push(
        `Metrics version did not advance: before ${versionBefore}, after ${versionAfter}`,
      );
    }
    if (navTypeBefore !== 'unknown' && navTypeAfter !== navTypeBefore) {
      verificationErrors.push(
        `Navigation type changed from ${navTypeBefore} to ${navTypeAfter}`,
      );
    }

    if (consoleErrors.length) {
      verificationErrors.push(`Console errors: ${consoleErrors.join('\n')}`);
    }

    if (verificationErrors.length) {
      throw new Error(verificationErrors.join('\n'));
    }

    console.log('Feature 243 metrics SSE verification ok');
  } catch (err) {
    console.error('Feature 243 metrics SSE verification failed:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
