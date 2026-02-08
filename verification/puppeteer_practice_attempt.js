const puppeteer = require('../client/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');
const { selectSource } = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'dashboard-practice-attempt-grading.png';
const source = process.env.TACTIX_SOURCE || 'chesscom';

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
    console.log('Navigating to UI...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1');
    await selectSource(page, source);

    await page.$$eval('h3', (headers) => {
      const target = headers.find((header) =>
        (header.textContent || '').includes('Practice attempt'),
      );
      const button = target?.closest('[role="button"]');
      if (button) {
        (button).click();
      }
    });

    console.log('Refreshing metrics to load practice queue...');
    await page.$$eval(
      'button',
      (buttons, label) => {
        const target = buttons.find(
          (btn) => btn.textContent && btn.textContent.includes(label),
        );
        if (target) target.click();
      },
      'Refresh metrics',
    );

    await page.waitForSelector('h3', { timeout: 60000 });
    await new Promise((resolve) => setTimeout(resolve, 2000));
    await page.waitForFunction(
      () => {
        const input = document.querySelector('input[placeholder*="UCI"]');
        if (!(input instanceof HTMLInputElement)) return false;
        const visible = input.offsetParent !== null;
        return visible && !input.disabled;
      },
      { timeout: 60000 },
    );
    let input;
    try {
      input = await page.waitForSelector('input[placeholder*="UCI"]', {
        timeout: 60000,
      });
    } catch (err) {
      const placeholders = await page.$$eval('input', (inputs) =>
        inputs.map((inputEl) => inputEl.getAttribute('placeholder')),
      );
      console.error('Available input placeholders:', placeholders);
      throw err;
    }
    if (!input) {
      throw new Error('Practice attempt input not found (queue may be empty).');
    }

    const bestLabel = await page.$$eval('span', (spans) => {
      const best = spans.find((span) => span.textContent?.startsWith('Best '));
      return best?.textContent || '';
    });
    const rawBestMove = bestLabel.replace('Best ', '').trim();
    const bestMove = rawBestMove && rawBestMove !== '--' ? rawBestMove : 'e2e4';

    const inputSelector = 'input[placeholder*="UCI"]';
    const submitSelector = 'button';

    const illegalMove = `${bestMove.slice(0, 2)}${bestMove.slice(0, 2)}`;
    await page.click(inputSelector, { clickCount: 3 });
    await page.keyboard.type(illegalMove);
    await page.$$eval(submitSelector, (buttons) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes('Submit attempt'),
      );
      if (target) target.click();
    });
    await page.waitForFunction(
      () =>
        Array.from(document.querySelectorAll('p')).some((el) =>
          el.textContent?.includes('Illegal move'),
        ),
      { timeout: 60000 },
    );

    await page.click(inputSelector, { clickCount: 3 });
    await page.keyboard.type(bestMove);
    await page.$$eval(submitSelector, (buttons) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes('Submit attempt'),
      );
      if (target) target.click();
    });

    await page.waitForSelector('span', { timeout: 60000 });
    await new Promise((resolve) => setTimeout(resolve, 1500));

    const outDir = path.resolve(__dirname);
    fs.mkdirSync(outDir, { recursive: true });
    const outPath = path.join(outDir, screenshotName);
    await page.screenshot({ path: outPath, fullPage: true });
    console.log('Saved screenshot to', outPath);

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
    console.error('Practice attempt verification failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
