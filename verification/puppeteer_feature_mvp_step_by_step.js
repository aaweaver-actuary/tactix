const fs = require('fs');
const path = require('path');
const puppeteer = require('../client/node_modules/puppeteer');
const { Chess } = require('../client/node_modules/chess.js');
const {
  attachConsoleCapture,
  captureScreenshot,
} = require('./helpers/puppeteer_capture');
const {
  selectSource,
  ensurePracticeCardExpanded,
  getFenFromPage,
} = require('./enter_submit_helpers');
const {
  openFiltersModal,
  closeFiltersModal,
} = require('./helpers/filters_modal_helpers');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const dashboardScreenshot =
  process.env.TACTIX_SCREENSHOT_DASHBOARD ||
  'feature-mvp-step-dashboard-2026-02-10.png';
const practiceScreenshot =
  process.env.TACTIX_SCREENSHOT_PRACTICE ||
  'feature-mvp-step-practice-2026-02-10.png';

const selectors = {
  hero: '[data-testid="dashboard-hero"]',
  runAction: '[data-testid="action-run"]',
  timeControl: '[data-testid="filter-time-control"]',
  motifBreakdown: '[data-testid="motif-breakdown"]',
  timeTrouble: '[data-testid="time-trouble-correlation"]',
  practiceStart: '[data-testid="practice-start"]',
  practiceRow: '[data-testid^="practice-queue-row-"]',
  chessboardModal: '[data-testid="chessboard-modal"]',
};

const sourceHeadings = {
  lichess: 'Lichess',
  chesscom: 'Chess.com',
};

async function assertHeroSource(page, source) {
  await page.waitForSelector(selectors.hero, { timeout: 60000 });
  await page.waitForFunction(
    (selector, token) => {
      const heading = document.querySelector(selector)?.querySelector('h1');
      return heading?.textContent?.includes(token);
    },
    { timeout: 60000 },
    selectors.hero,
    sourceHeadings[source],
  );
  await page.waitForFunction(
    (selector) => {
      const button = document.querySelector(selector);
      return button instanceof HTMLButtonElement && !button.disabled;
    },
    { timeout: 60000 },
    selectors.runAction,
  );
}

async function assertTimeControlOptions(page) {
  await openFiltersModal(page);
  await page.waitForSelector(selectors.timeControl, { timeout: 60000 });
  const options = await page.$eval(selectors.timeControl, (selectEl) =>
    Array.from(selectEl.querySelectorAll('option')).map((opt) => opt.value),
  );
  if (!options.includes('all')) {
    throw new Error('Missing time control option: all');
  }
  const hasKnownControl = ['bullet', 'blitz', 'rapid'].some((value) =>
    options.includes(value),
  );
  if (!hasKnownControl) {
    throw new Error('Expected at least one specific time control option.');
  }
  await closeFiltersModal(page);
}

async function getMotifIds(page) {
  await page.waitForSelector(selectors.motifBreakdown, { timeout: 60000 });
  return page.$$eval(
    '[data-testid="motif-breakdown"] [data-motif-id]',
    (cards) => cards.map((card) => card.getAttribute('data-motif-id') || ''),
  );
}

function assertMotifIds(motifs) {
  if (!motifs.includes('hanging_piece')) {
    throw new Error('Motif breakdown missing hanging_piece card.');
  }
  if (!motifs.includes('mate')) {
    throw new Error('Motif breakdown missing mate card.');
  }
}

async function assertTrendAndTimeTroubleCards(page) {
  await page.waitForSelector(selectors.timeTrouble, { timeout: 60000 });
  const trendBadge = await page.$$eval('h3', (headers) => {
    const card = headers.find((header) =>
      (header.textContent || '').includes('Motif trends'),
    );
    if (!card) return '';
    const badge = card.parentElement?.querySelector('span');
    return badge?.textContent || '';
  });
  if (!trendBadge.includes('Rolling 7/30 days')) {
    throw new Error('Motif trends should show rolling 7/30 days.');
  }

  const timeTroubleRows = await page.$$eval(
    `${selectors.timeTrouble} table tbody tr`,
    (rows) => rows.length,
  );
  if (timeTroubleRows <= 0) {
    throw new Error('Time-trouble correlation table should have rows.');
  }
}

async function startPracticeAttempt(page, sources) {
  for (const source of sources) {
    if (source) {
      await selectSource(page, source);
      await assertHeroSource(page, source);
    }
    await ensurePracticeCardExpanded(page);
    const startButton = await page.$(selectors.practiceStart);
    if (!startButton) {
      continue;
    }

    const queueCount = await page.$$eval(
      selectors.practiceRow,
      (rows) => rows.length,
    );
    if (queueCount <= 0) {
      continue;
    }

    await page.click(selectors.practiceStart);
    await page.waitForSelector(selectors.chessboardModal, { timeout: 60000 });
    await page.waitForFunction(
      () => {
        const modal = document.querySelector('[data-testid="chessboard-modal"]');
        const input = modal?.querySelector('input[placeholder*="UCI"]');
        if (!(input instanceof HTMLInputElement)) return false;
        return input.offsetParent !== null && !input.disabled;
      },
      { timeout: 60000 },
    );

    const fen = await getFenFromPage(page);
    const board = new Chess(fen);
    const attemptMove = board
      .moves({ verbose: true })
      .map((move) => `${move.from}${move.to}${move.promotion || ''}`)
      .find(Boolean);
    if (!attemptMove) {
      throw new Error('Unable to find a legal move for practice attempt.');
    }

    const inputSelector =
      '[data-testid="chessboard-modal"] input[placeholder*="UCI"]';
    await page.click(inputSelector, { clickCount: 3 });
    await page.keyboard.type(attemptMove);
    await page.$$eval('button', (buttons) => {
      const target = buttons.find(
        (btn) => btn.textContent && btn.textContent.includes('Submit attempt'),
      );
      if (target) target.click();
    });

    await page.waitForFunction(
      () =>
        Array.from(document.querySelectorAll('span')).some((el) =>
          ['Correct', 'Missed'].some((label) =>
            el.textContent?.includes(label),
          ),
        ),
      { timeout: 60000 },
    );

    await page.waitForSelector('[data-testid="practice-best-move"]', {
      timeout: 60000,
    });
    return;
  }
  throw new Error('Practice start button not available for any source.');
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const consoleErrors = attachConsoleCapture(page);

  try {
    console.log('Loading dashboard...');
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
    await page.waitForSelector(selectors.hero, { timeout: 60000 });

    console.log('Checking time control options...');
    await assertTimeControlOptions(page);
    console.log('Selecting lichess source...');
    await selectSource(page, 'lichess');
    await assertHeroSource(page, 'lichess');
    let motifs = await getMotifIds(page);
    if (!motifs.length) {
      console.log('Switching to chesscom source for motif data...');
      await selectSource(page, 'chesscom');
      await assertHeroSource(page, 'chesscom');
      motifs = await getMotifIds(page);
    }
    if (!motifs.length) {
      throw new Error('Motif breakdown has no rows for any source.');
    }
    console.log('Validating motif breakdown...');
    assertMotifIds(motifs);
    console.log('Validating trend and time-trouble cards...');
    await assertTrendAndTimeTroubleCards(page);

    const outDir = path.resolve(__dirname);
    const dashboardPath = await captureScreenshot(
      page,
      outDir,
      dashboardScreenshot,
    );
    console.log('Saved screenshot to', dashboardPath);

    console.log('Starting practice attempt...');
    await startPracticeAttempt(page, ['lichess', 'chesscom']);
    fs.mkdirSync(outDir, { recursive: true });
    const practicePath = path.join(outDir, practiceScreenshot);
    await page.screenshot({ path: practicePath, fullPage: true });
    console.log('Saved screenshot to', practicePath);

    if (consoleErrors.length) {
      throw new Error(`Console errors detected: ${consoleErrors.join('\n')}`);
    }
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
