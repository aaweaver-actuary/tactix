const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const baseUrl = process.env.TACTIX_AIRFLOW_URL || 'http://localhost:8080';
const dagId = process.env.TACTIX_DAG_ID || 'daily_game_sync';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  `airflow-${dagId}-${new Date().toISOString().slice(0, 10)}.png`;
const expectedDate =
  process.env.TACTIX_EXPECT_DATE || new Date().toISOString().slice(0, 10);
const airflowUser = process.env.AIRFLOW_USERNAME || 'admin';
const airflowPass = process.env.AIRFLOW_PASSWORD || 'admin';

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
  await page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 60000 });
}

async function clickFirst(page, selectors, description) {
  for (const selector of selectors) {
    const handle = await page.$(selector);
    if (handle) {
      await handle.click();
      return;
    }
  }
  throw new Error(`${description} not found`);
}

async function findButtonByText(page, texts) {
  const buttons = await page.$$('button');
  for (const button of buttons) {
    const label = await page.evaluate((el) => el.textContent || '', button);
    if (texts.some((text) => label.includes(text))) {
      return button;
    }
  }
  return null;
}

async function clickByText(page, selectors, texts) {
  for (const selector of selectors) {
    const handles = await page.$$(selector);
    for (const handle of handles) {
      const label = await page.evaluate((el) => (el.textContent || '').trim(), handle);
      if (texts.some((text) => label.includes(text))) {
        try {
          await handle.click();
        } catch (err) {
          await page.evaluate((el) => el.click(), handle);
        }
        return true;
      }
    }
  }
  return false;
}

async function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function dismissModal(page) {
  const modal = await page.$('div[role="dialog"], div[aria-modal="true"]');
  if (!modal) return;
  try {
    const closed = await clickByText(
      page,
      ['button', '[role="button"]'],
      ['OK', 'Close', 'Cancel', '×'],
    );
    if (closed) {
      await delay(1000);
      return;
    }
    const fallback = await page.$('button[aria-label="Close"], [aria-label="Close"]');
    if (fallback) {
      await page.evaluate((el) => el.click(), fallback);
      await delay(1000);
    }
  } catch (err) {
    // ignore modal dismissal issues
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
    const errorText = request.failure()?.errorText || 'unknown';
    if (errorText.includes('ERR_ABORTED')) {
      return;
    }
    consoleErrors.push(`Request failed: ${request.url()} (${errorText})`);
  });

  try {
    await page.goto(`${baseUrl}/dags/${dagId}/grid`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await delay(3000);
    await dismissModal(page);
    await maybeLogin(page);
    await page.goto(`${baseUrl}/dags/${dagId}/grid`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    let triggered = false;
    try {
      await page.waitForSelector('[aria-label="Trigger DAG"]', {
        timeout: 60000,
      });
      const triggerSelector = '[aria-label="Trigger DAG"]';
      await page.waitForSelector(triggerSelector, { timeout: 60000 });
      await page.evaluate((sel) => {
        const el = document.querySelector(sel);
        if (!el) throw new Error('Trigger DAG element missing');
        el.scrollIntoView();
        el.click();
      }, triggerSelector);
      triggered = true;
    } catch (err) {
      try {
        await clickFirst(
          page,
          [
            '[aria-label*="Trigger"]',
            '[title*="Trigger"]',
            '[data-testid*="trigger"]',
          ],
          'Trigger DAG button',
        );
        triggered = true;
      } catch (innerErr) {
        const triggerButton = await findButtonByText(page, ['Trigger DAG', 'Trigger']);
        if (triggerButton) {
          try {
            await triggerButton.click();
          } catch (clickErr) {
            await page.evaluate((el) => el.click(), triggerButton);
          }
          triggered = true;
        }
      }
    }

    if (!triggered) {
      const openedMenu = await clickByText(
        page,
        ['button'],
        ['Actions', 'More', 'Menu'],
      );
      if (openedMenu) {
        const triggeredFromMenu = await clickByText(
          page,
          ['button', 'a', '[role="menuitem"]'],
          ['Trigger DAG', 'Trigger'],
        );
        if (!triggeredFromMenu) {
          throw new Error('Trigger DAG button not found');
        }
      } else {
        throw new Error('Trigger DAG button not found');
      }
    }

    try {
      await page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 15000 });
    } catch (err) {
      // ignore if no navigation occurred
    }

    try {
      const dialog = await page.$('div[role="dialog"], div[aria-modal="true"]');
      if (dialog) {
        const confirmButton = await dialog.$('button[type="submit"], button[data-testid="confirm"], button');
        if (confirmButton) {
          try {
            await confirmButton.click();
          } catch (err) {
            await page.evaluate((el) => el.click(), confirmButton);
          }
        }
      }
    } catch (err) {
      // ignore dialog handling errors during navigation
    }

    await page.waitForSelector('table', { timeout: 60000 });
    await delay(3000);

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });

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
    } catch (screenshotErr) {
      console.error('Failed to capture failure screenshot:', screenshotErr);
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Airflow daily_game_sync trigger verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();