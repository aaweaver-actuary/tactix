const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const DASHBOARD_URL = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const SCREENSHOT_NAME =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'feature-dashboard-cards-collapsible-move-2026-02-08.png';

async function getCardOrder(page) {
  return page.$$eval('[data-card-id]', (elements) =>
    elements.map((el) => el.getAttribute('data-card-id')),
  );
}

async function ensureCollapsed(page, cardSelector) {
  const stateSelector = `${cardSelector} [data-state]`;
  const state = await page.$eval(stateSelector, (el) =>
    el.getAttribute('data-state'),
  );
  if (state !== 'collapsed') {
    await page.click(`${cardSelector} [role="button"]`);
    await page.waitForSelector(`${cardSelector} [data-state="collapsed"]`, {
      timeout: 60000,
    });
  }
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
    consoleErrors.push(
      `Request failed: ${request.url()} (${request.failure()?.errorText || 'unknown'})`,
    );
  });

  try {
    await page.goto(DASHBOARD_URL, {
      waitUntil: 'networkidle0',
      timeout: 60000,
    });

    await page.waitForSelector('[data-card-id]', { timeout: 60000 });

    const cardIds = await getCardOrder(page);
    if (!cardIds.length) {
      throw new Error('No dashboard cards were found.');
    }

    for (const cardId of cardIds) {
      const cardSelector = `[data-testid="dashboard-card-${cardId}"]`;
      const headerSelector = `${cardSelector} [role="button"]`;
      await page.waitForSelector(headerSelector, { timeout: 60000 });

      const headerMeta = await page.$eval(headerSelector, (el) => ({
        expanded: el.getAttribute('aria-expanded'),
        controls: el.getAttribute('aria-controls'),
      }));
      if (!headerMeta.controls) {
        throw new Error(`Card ${cardId} missing aria-controls on header.`);
      }

      const targetState = headerMeta.expanded === 'true' ? 'collapsed' : 'expanded';
      await page.click(headerSelector);
      await page.waitForSelector(
        `${cardSelector} [data-state="${targetState}"]`,
        { timeout: 60000 },
      );

      const resetState = targetState === 'collapsed' ? 'expanded' : 'collapsed';
      await page.click(headerSelector);
      await page.waitForSelector(
        `${cardSelector} [data-state="${resetState}"]`,
        { timeout: 60000 },
      );

      await ensureCollapsed(page, cardSelector);

      const dragHandleSelector =
        `${cardSelector} [aria-label^="Reorder "]`;
      await page.waitForSelector(dragHandleSelector, { timeout: 60000 });
      const dragVisible = await page.$eval(dragHandleSelector, (el) => {
        const styles = window.getComputedStyle(el);
        return styles.opacity !== '0' && styles.pointerEvents !== 'none';
      });
      if (!dragVisible) {
        throw new Error(`Drag handle not visible for ${cardId}.`);
      }
    }

    const initialOrder = await getCardOrder(page);
    const sourceId = initialOrder[0];
    if (!sourceId) {
      throw new Error('No card available for reorder verification.');
    }
    const targetIndex = initialOrder.length - 1;
    const sourceSelector = `[data-testid="dashboard-card-${sourceId}"]`;
    await ensureCollapsed(page, sourceSelector);

    const dragHandleSelector =
      `${sourceSelector} [aria-label^="Reorder "]`;
    await page.waitForSelector(dragHandleSelector, { timeout: 60000 });
    await page.focus(dragHandleSelector);
    await page.keyboard.press('Space');

    for (let i = 0; i < targetIndex; i += 1) {
      // eslint-disable-next-line no-await-in-loop
      await page.keyboard.press('ArrowDown');
    }

    await page.keyboard.press('Space');

    await page.waitForFunction(
      (previousOrder) => {
        const current = Array.from(
          document.querySelectorAll('[data-card-id]'),
        ).map((el) => el.getAttribute('data-card-id'));
        return current.join('|') !== previousOrder.join('|');
      },
      { timeout: 60000 },
      initialOrder,
    );

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, SCREENSHOT_NAME);
    await page.screenshot({ path: outPath, fullPage: true });

    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
      process.exit(1);
    }
  } catch (err) {
    try {
      const outDir = path.resolve(__dirname);
      fs.mkdirSync(outDir, { recursive: true });
      const outPath = path.join(outDir, `failed-${SCREENSHOT_NAME}`);
      await page.screenshot({ path: outPath, fullPage: true });
      console.error('Saved failure screenshot to', outPath);
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Dashboard cards verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
