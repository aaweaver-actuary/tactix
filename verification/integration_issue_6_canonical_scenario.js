const puppeteer = require('../client/node_modules/puppeteer');

const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

async function fetchJson(page, path) {
  const url = `${apiBase}${path}`;
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
  const raw = await page.evaluate(() => document.body.innerText || '');
  return JSON.parse(raw);
}

function countResults(recentGames, expected) {
  return recentGames.filter((row) => row && normalizeResult(row) === expected)
    .length;
}

function normalizeResult(row) {
  const result = row?.result;
  const userColor = row?.user_color;
  if (!result) return 'unknown';
  if (result === '1/2-1/2') return 'draw';
  if (result === '1-0') {
    if (userColor === 'white') return 'win';
    if (userColor === 'black') return 'loss';
  }
  if (result === '0-1') {
    if (userColor === 'black') return 'win';
    if (userColor === 'white') return 'loss';
  }
  return result;
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setExtraHTTPHeaders({ Authorization: `Bearer ${apiToken}` });

  try {
    const params = new URLSearchParams({
      source: 'chesscom',
      time_control: 'bullet',
      start_date: '2026-02-01',
      end_date: '2026-02-01',
    });
    const dashboard = await fetchJson(
      page,
      `/api/dashboard?${params.toString()}`,
    );
    const recentGames = Array.isArray(dashboard.recent_games)
      ? dashboard.recent_games
      : [];

    if (recentGames.length !== 2) {
      throw new Error(`Expected 2 recent games, found ${recentGames.length}`);
    }

    const wins = countResults(recentGames, 'win');
    const losses = countResults(recentGames, 'loss');

    if (wins !== 1 || losses !== 1) {
      throw new Error(
        `Expected 1 win and 1 loss, found ${wins} wins and ${losses} losses`,
      );
    }

    const lossGame = recentGames.find(
      (row) => row && normalizeResult(row) === 'loss',
    );
    if (!lossGame || !lossGame.game_id) {
      throw new Error(
        'Expected loss game with game_id in recent games payload',
      );
    }

    const practiceQueue = await fetchJson(
      page,
      '/api/practice/queue?source=chesscom&include_failed_attempt=0&limit=10',
    );
    const items = Array.isArray(practiceQueue.items) ? practiceQueue.items : [];

    if (items.length !== 2) {
      throw new Error(`Expected 2 practice queue items, found ${items.length}`);
    }

    const mismatchedGame = items.find(
      (item) => item && String(item.game_id) !== String(lossGame.game_id),
    );
    if (mismatchedGame) {
      throw new Error(
        'Expected all practice queue items to come from the loss game',
      );
    }

    const nonHanging = items.find(
      (item) =>
        item && (item.motif !== 'hanging_piece' || item.result !== 'missed'),
    );
    if (nonHanging) {
      throw new Error(
        'Expected practice queue items to be missed hanging_piece tactics',
      );
    }

    console.log('Issue 6 integration check ok');
  } catch (err) {
    console.error('Issue 6 integration check failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
