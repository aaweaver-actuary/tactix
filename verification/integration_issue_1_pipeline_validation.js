const puppeteer = require('../client/node_modules/puppeteer');

const baseUrl = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

async function fetchDashboard(page) {
  const params = new URLSearchParams({
    source: 'chesscom',
    motif: 'hanging_piece',
    start_date: '2026-02-01',
    end_date: '2026-02-01',
  });
  const url = `${baseUrl}/api/dashboard?${params.toString()}`;
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
  const raw = await page.evaluate(() => document.body.innerText || '');
  return JSON.parse(raw);
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setExtraHTTPHeaders({ Authorization: `Bearer ${apiToken}` });

  try {
    const payload = await fetchDashboard(page);
    const recentGames = payload.recent_games || [];
    const tactics = payload.tactics || [];

    if (recentGames.length !== 2) {
      throw new Error(`Expected 2 recent games, found ${recentGames.length}`);
    }

    const results = tactics.map((row) => row.result).filter(Boolean);
    const motifs = tactics.map((row) => row.motif).filter(Boolean);

    if (!motifs.includes('hanging_piece')) {
      throw new Error('Expected hanging_piece tactics in dashboard payload');
    }
    if (!results.includes('failed_attempt')) {
      throw new Error('Expected a failed_attempt hanging_piece tactic');
    }

    console.log('Issue 1 integration check ok');
  } catch (err) {
    console.error('Issue 1 integration check failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
