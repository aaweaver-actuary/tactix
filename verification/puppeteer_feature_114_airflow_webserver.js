const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');

const baseUrl = process.env.TACTIX_AIRFLOW_URL || 'http://localhost:8080';
const dagId = process.env.TACTIX_DAG_ID || 'daily_game_sync';
const screenshotPrefix =
  process.env.TACTIX_SCREENSHOT_PREFIX ||
  `feature-114-airflow-webserver-${new Date().toISOString().slice(0, 10)}`;
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

async function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
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
    await delay(3000);
    await dismissModal(page);
    await maybeLogin(page);
    await page.goto(`${baseUrl}/home`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('table', { timeout: 60000 });

    const dagListHasRows = await page.evaluate(() => {
      const rows = document.querySelectorAll('table tbody tr');
      return rows.length > 0;
    });
    if (!dagListHasRows) {
      throw new Error('Airflow DAG list is empty');
    }

    const hasTargetDag = await page.evaluate((targetDag) => {
      const rows = Array.from(document.querySelectorAll('table tbody tr'));
      return rows.some((row) => row.textContent?.includes(targetDag));
    }, dagId);
    if (!hasTargetDag) {
      throw new Error(`Expected DAG ${dagId} not found in list`);
    }

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

    let triggered = false;
    try {
      await page.waitForSelector('[aria-label="Trigger DAG"]', { timeout: 60000 });
      await page.evaluate(() => {
        const trigger = document.querySelector('[aria-label="Trigger DAG"]');
        if (!trigger) throw new Error('Trigger DAG element missing');
        trigger.scrollIntoView();
        trigger.click();
      });
      triggered = true;
    } catch (err) {
      const clicked = await clickByText(page, ['button', '[role="button"]'], [
        'Trigger DAG',
        'Trigger',
      ]);
      if (clicked) {
        triggered = true;
      } else {
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
      const openedMenu = await clickByText(page, ['button'], ['Actions', 'More', 'Menu']);
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
      // ignore dialog handling errors
    }

    await page.waitForSelector('table', { timeout: 60000 });
    await delay(3000);

    await page.screenshot({
      path: path.join(outDir, `${screenshotPrefix}-trigger.png`),
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
