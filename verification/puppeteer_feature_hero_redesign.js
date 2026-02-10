const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const desktopScreenshot =
  process.env.TACTIX_SCREENSHOT_DESKTOP ||
  'feature-hero-redesign-desktop-2026-02-10.png';
const mobileScreenshot =
  process.env.TACTIX_SCREENSHOT_MOBILE ||
  'feature-hero-redesign-mobile-2026-02-10.png';
const {
  getHeroStatus,
  waitForHero,
} = require('./helpers/hero_redesign_helpers');

const assertHeroControls = async (page) => {
  await waitForHero(page);
  const { missing } = await getHeroStatus(page);

  if (missing.length) {
    throw new Error(`Missing hero controls: ${missing.join(', ')}`);
  }
};

const openHeroPage = async (page, viewport) => {
  await page.setViewport(viewport);
  await page.goto(targetUrl, { waitUntil: 'networkidle0' });
  await assertHeroControls(page);
};

const assertConsoleClean = (consoleErrors) => {
  if (consoleErrors.length) {
    throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
  }
};

const captureHeroScreenshot = async (browser, viewport, screenshotName) => {
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  await openHeroPage(page, viewport);

  const outPath = await captureScreenshot(
    page,
    path.resolve(__dirname),
    screenshotName,
  );

  assertConsoleClean(consoleErrors);

  await page.close();
  return outPath;
};

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });

  try {
    const desktopPath = await captureHeroScreenshot(
      browser,
      { width: 1280, height: 720 },
      desktopScreenshot,
    );
    console.log('Saved screenshot to', desktopPath);

    const mobilePath = await captureHeroScreenshot(
      browser,
      {
        width: 390,
        height: 844,
        isMobile: true,
        deviceScaleFactor: 2,
      },
      mobileScreenshot,
    );
    console.log('Saved screenshot to', mobilePath);
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
