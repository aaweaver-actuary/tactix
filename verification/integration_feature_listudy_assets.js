const puppeteer = require('../client/node_modules/puppeteer');
const { selectSource } = require('./enter_submit_helpers');

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

    const hasPieceAssets = await page.evaluate(() =>
      Array.from(document.querySelectorAll('img')).some((img) =>
        img.getAttribute('src')?.includes('/pieces/cburnett/'),
      ),
    );

    if (!hasPieceAssets) {
      throw new Error('Listudy piece assets were not rendered.');
    }

    const hasListudyCardTexture = await page.evaluate(() => {
      const card = document.querySelector('.card');
      if (!card) return false;
      return window.getComputedStyle(card).backgroundImage.includes(
        'listudy-brown',
      );
    });

    if (!hasListudyCardTexture) {
      throw new Error('Listudy board texture missing from card surfaces.');
    }

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }

    console.log('Listudy assets integration check ok');
  } finally {
    await browser.close();
  }
})();
