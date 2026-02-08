const puppeteer = require('../client/node_modules/puppeteer');
const {
  buildFallbackMove,
  getBestMoveFromPage,
  getFenFromPage,
  selectSource,
} = require('./enter_submit_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
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
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector('h1');
    await selectSource(page, source);

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

    const inputSelector = 'input[placeholder*="UCI"]';
    const input = await page.waitForSelector(inputSelector, { timeout: 60000 });
    if (!input) {
      throw new Error('Practice attempt input not found (queue may be empty).');
    }

    const bestMoveFromPage = await getBestMoveFromPage(page);
    const bestMove =
      bestMoveFromPage && bestMoveFromPage.trim().length >= 4
        ? bestMoveFromPage
        : buildFallbackMove(await getFenFromPage(page));

    await page.click(inputSelector, { clickCount: 3 });
    await page.keyboard.type(bestMove);
    await page.keyboard.press('Enter');

    await page.waitForFunction(
      () => {
        const spans = Array.from(document.querySelectorAll('span'));
        const feedback = spans.some((el) =>
          ['Correct', 'Missed'].includes(el.textContent?.trim() || ''),
        );
        const error = Array.from(document.querySelectorAll('p')).some((el) =>
          (el.textContent || '').includes('Enter a move') ||
          (el.textContent || '').includes('Illegal move') ||
          (el.textContent || '').includes('Failed to submit practice attempt'),
        );
        return feedback || error;
      },
      { timeout: 60000 },
    );

    const result = await page.evaluate(() => {
      const spanText = Array.from(document.querySelectorAll('span'))
        .map((el) => el.textContent?.trim() || '')
        .find((text) => ['Correct', 'Missed'].includes(text));
      const errorText = Array.from(document.querySelectorAll('p'))
        .map((el) => el.textContent || '')
        .find(
          (text) =>
            text.includes('Enter a move') ||
            text.includes('Illegal move') ||
            text.includes('Failed to submit practice attempt'),
        );
      return { feedback: spanText || null, error: errorText || null };
    });

    if (result.error) {
      throw new Error(`Practice submit error: ${result.error}`);
    }

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Enter submit integration verified.');
  } finally {
    await browser.close();
  }
})();
