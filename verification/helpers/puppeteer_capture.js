const fs = require('fs');
const path = require('path');

const attachConsoleCapture = (page) => {
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

  return consoleErrors;
};

const captureScreenshot = async (page, outDir, screenshotName) => {
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, screenshotName);
  await page.screenshot({ path: outPath, fullPage: true });
  return outPath;
};

module.exports = { attachConsoleCapture, captureScreenshot };
