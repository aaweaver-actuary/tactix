const puppeteer = require('../client/node_modules/puppeteer');

const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

async function fetchJson(page, path) {
  const url = `${apiBase}${path}`;
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
  const raw = await page.evaluate(() => document.body.innerText || '');
  return JSON.parse(raw);
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setExtraHTTPHeaders({ Authorization: `Bearer ${apiToken}` });

  try {
    const rawPgns = await fetchJson(page, '/api/postgres/raw_pgns');
    const sources = Array.isArray(rawPgns.sources) ? rawPgns.sources : [];
    const chesscom = sources.find((row) => row && row.source === 'chesscom');
    if (!chesscom || (chesscom.distinct_games || 0) < 2) {
      throw new Error('Expected at least 2 chesscom games in Postgres raw PGNs');
    }

    const analysis = await fetchJson(page, '/api/postgres/analysis?limit=50');
    const tactics = Array.isArray(analysis.tactics) ? analysis.tactics : [];
    const missed = tactics.filter(
      (row) => row && row.motif === 'hanging_piece' && row.result === 'missed',
    );
    if (!missed.length) {
      throw new Error('Expected missed hanging_piece tactics in Postgres analysis');
    }

    const targetGame = missed.filter(
      (row) => String(row.game_id) === '1234567890',
    );
    if (targetGame.length < 2) {
      throw new Error('Expected at least 2 missed hanging_piece tactics for game 1234567890');
    }

    console.log('Issue 2 integration check ok');
  } catch (err) {
    console.error('Issue 2 integration check failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
