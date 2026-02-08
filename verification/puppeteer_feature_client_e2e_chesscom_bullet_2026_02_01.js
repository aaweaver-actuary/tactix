const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const { waitForHealth, runPipeline } = require('./helpers/backend_canonical_helpers');
const {
  applyFilters,
  buildClientE2EConfig,
  ensureCardExpanded,
  launchBackend,
  startDevServer,
  step,
} = require('./helpers/client_e2e_helpers');

const {
  rootDir,
  clientDir,
  backendCmd,
  backendPort,
  devServerPort,
  apiBase,
  apiToken,
  targetUrl,
  backendRunning,
  testUser,
  duckdbPath,
  screenshotName,
  runDate,
} = buildClientE2EConfig({
  baseDir: __dirname,
  backendPortDefault: '8004',
  uiPortDefault: '5181',
  duckdbFileName: 'feature_client_e2e_chesscom_bullet_2026_02_01.duckdb',
  screenshotNameDefault: 'feature-client-e2e-chesscom-bullet-2026-02-01.png',
});

(async () => {
  let backend = null;
  let devServer = null;
  let browser = null;
  let page = null;
  let consoleErrors = [];

  try {
    if (!backendRunning) {
      console.log('Starting backend...');
      fs.mkdirSync(path.dirname(duckdbPath), { recursive: true });
      if (fs.existsSync(duckdbPath)) {
        fs.unlinkSync(duckdbPath);
      }
      backend = await launchBackend({
        rootDir,
        backendCmd,
        backendPort,
        apiToken,
        duckdbPath,
        testUser,
      });
    }

    console.log('Waiting for backend health...');
    await waitForHealth({ apiBase, apiToken });

    console.log('Running pipeline fixture...');
    await runPipeline({
      apiBase,
      apiToken,
      source: 'chesscom',
      profile: 'bullet',
      userId: testUser,
      startDate: runDate,
      endDate: runDate,
      useFixture: true,
      fixtureName: 'chesscom_2_bullet_games.pgn',
      resetDb: true,
      retries: 3,
      retryDelayMs: 1000,
    });

    console.log('Starting dev server...');
    devServer = await startDevServer({
      clientDir,
      devServerPort,
      apiBase,
    });

    console.log('Launching browser...');
    browser = await puppeteer.launch({ headless: 'new' });
    page = await browser.newPage();
    consoleErrors = attachConsoleCapture(page);

    console.log('Loading dashboard...');
    await step('Page navigation', async () => {
      await page.goto(targetUrl, { waitUntil: 'networkidle0', timeout: 60000 });
      await page.waitForSelector('[data-testid="filter-source"]', {
        timeout: 60000,
      });
    });

    console.log('Applying filters...');
    await step('Filter updates', async () => {
      await applyFilters(page, runDate);
    });

    console.log('Expanding cards...');
    await step('Expand recent games', async () => {
      await ensureCardExpanded(page, 'recent-games-card');
    });
    await step('Expand practice queue', async () => {
      await ensureCardExpanded(page, 'practice-queue-card');
    });

    console.log('Waiting for rows...');
    await step('Table readiness', async () => {
      await page.waitForFunction(
        () => {
          const recentRows = document.querySelectorAll(
            '[data-testid^="recent-games-row-"]',
          ).length;
          const practiceRows = document.querySelectorAll(
            '[data-testid^="practice-queue-row-"]',
          ).length;
          const recentText = document.querySelector(
            '[data-testid="recent-games-card"]',
          )?.textContent?.toLowerCase() || '';
          const practiceText = document.querySelector(
            '[data-testid="practice-queue-card"]',
          )?.textContent?.toLowerCase() || '';
          const recentReady =
            recentRows > 0 || recentText.includes('no rows');
          const practiceReady =
            practiceRows > 0 || practiceText.includes('no rows');
          return recentReady && practiceReady;
        },
        { timeout: 120000 },
      );
    });

    const recentRows = await page.$$('[data-testid^="recent-games-row-"]');
    const practiceRows = await page.$$('[data-testid^="practice-queue-row-"]');

    if (recentRows.length !== 2 || practiceRows.length !== 2) {
      throw new Error(
        `Expected 2 recent games rows and 2 practice rows, got ${recentRows.length} and ${practiceRows.length}.`,
      );
    }

    const resultLabels = await page.$$eval(
      '[data-testid^="recent-games-row-"]',
      (rows) =>
        rows.map((row) => {
          const cells = Array.from(row.querySelectorAll('td'));
          const resultCell = cells[2];
          return (resultCell?.textContent || '').trim().toLowerCase();
        }),
    );
    const winCount = resultLabels.filter((label) => label === 'win').length;
    const lossCount = resultLabels.filter((label) => label === 'loss').length;
    if (winCount !== 1 || lossCount !== 1) {
      throw new Error('Expected exactly one win and one loss in recent games');
    }

    const lossOpponent = await page.$$eval(
      '[data-testid^="recent-games-row-"]',
      (rows) => {
        for (const row of rows) {
          const cells = Array.from(row.querySelectorAll('td'));
          const resultCell = cells[2];
          const result = (resultCell?.textContent || '').trim().toLowerCase();
          if (result === 'loss') {
            return (cells[1]?.textContent || '').trim();
          }
        }
        return '';
      },
    );
    if (!lossOpponent) {
      throw new Error('Unable to determine loss opponent from recent games.');
    }

    const practiceLabels = await page.$$eval(
      '[data-testid^="practice-queue-row-"]',
      (rows) =>
        rows.map((row) => (row.textContent || '').toLowerCase()),
    );
    practiceLabels.forEach((text, index) => {
      if (!text.includes('missed')) {
        throw new Error(`Expected practice row ${index + 1} to be missed.`);
      }
    });

    for (const row of practiceRows) {
      await row.click();
      await page.waitForSelector('[data-testid="game-detail-modal"]', {
        visible: true,
      });
      await page.waitForSelector('[data-testid="game-detail-players"]');

      const playerText = await page.$eval(
        '[data-testid="game-detail-players"]',
        (node) => (node.textContent || '').toLowerCase(),
      );
      if (!playerText.includes(lossOpponent.toLowerCase())) {
        throw new Error(
          `Practice row not tied to loss opponent ${lossOpponent}.`,
        );
      }

      await page.click('[data-testid="game-detail-close"]');
      await page.waitForSelector('[data-testid="game-detail-modal"]', {
        hidden: true,
      });
    }

    const screenshotPath = await captureScreenshot(
      page,
      path.resolve(__dirname),
      screenshotName,
    );
    console.log('Saved screenshot to', screenshotPath);

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }
  } catch (err) {
    if (page) {
      try {
        const failurePath = await captureScreenshot(
          page,
          path.resolve(__dirname),
          `failed-${screenshotName}`,
        );
        console.error('Saved failure screenshot to', failurePath);
      } catch (screenshotErr) {
        console.error('Failed to capture failure screenshot:', screenshotErr);
      }
    }
    if (consoleErrors.length) {
      console.error('Console errors detected:', consoleErrors);
    }
    console.error('Client E2E verification failed:', err);
    process.exit(1);
  } finally {
    if (browser) await browser.close();
    if (devServer) devServer.kill();
    if (backend) backend.kill();
  }
})();
